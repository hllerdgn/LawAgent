"""
shadow_encoder.py  —  LawAgent Shadow Model Corpus Encoder
===========================================================

Production embedder.py'ye HİÇ DOKUNMADAN, shadow modeller için
corpus encoding ve Qdrant collection yönetimi sağlar.

Kullanım:
    python src/shadow_encoder.py --model-key shadow_mursit_large
    python src/shadow_encoder.py --model-key shadow_mursit_large --test-encode
    python src/shadow_encoder.py --model-key shadow_mursit_large --force-re-encode
    python src/shadow_encoder.py --model-key shadow_mursit_large --cleanup
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import sys
import time
import uuid
from typing import Iterator

# Proje dizin yapısı
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)

# sys.path düzelt — hem src/ hem BACKEND/ root erişilebilir olsun
for _p in [_SRC_DIR, _BACKEND_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# .env yükle
from dotenv import load_dotenv
for _env in [
    os.path.join(_BACKEND_DIR, ".env"),
    os.path.join(_BACKEND_DIR, "src", ".env"),
]:
    if os.path.exists(_env):
        load_dotenv(dotenv_path=_env)
        break

import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from config.embedding_models import (
    get_model_config,
    is_production_collection,
    list_shadow_models,
)
from services.qdrant_client import get_qdrant_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.ShadowEncoder")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        log.info(f"{kw.get('desc','İşlem')}...")
        return it

_DATA_DIR = os.path.join(_SRC_DIR, "data")
ENRICHED_CORPUS = os.path.join(_DATA_DIR, "chunk_corpus_enriched.json")
CHUNK_CORPUS = os.path.join(_DATA_DIR, "chunk_corpus.json")
DISTANCE_METRIC = qm.Distance.COSINE


# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_id_to_uint64(cid: str) -> int:
    return uuid.uuid5(uuid.NAMESPACE_DNS, str(cid)).int >> 64


def _load_corpus(test_mode: bool = False, limit: int = 100) -> list[dict]:
    path = ENRICHED_CORPUS if os.path.exists(ENRICHED_CORPUS) else CHUNK_CORPUS
    with open(path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    if test_mode:
        corpus = corpus[:limit]
        log.info(f"Test modu: İlk {limit} chunk kullanılıyor.")
    log.info(f"Corpus yüklendi: {len(corpus)} chunk ({os.path.basename(path)})")
    return corpus


def _build_encode_text(chunk: dict) -> str:
    """Production embedder ile aynı metin zenginleştirme mantığı."""
    source = chunk.get("source", "")
    text = chunk.get("text", "")
    if source == "yargitay":
        return f"Yargıtay Kararı {chunk.get('decision_id', '')}: {text}"
    return f"{chunk.get('law', '')} Madde {chunk.get('article_no', '')}: {text}"


def _qdrant_retry(func, *args, retries: int = 5, delay: float = 1.0, **kwargs):
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == retries - 1:
                raise
            wait = delay * (2 ** i)
            log.warning(f"Qdrant hata (deneme {i+1}/{retries}): {e}. {wait:.1f}s bekleniyor...")
            time.sleep(wait)


# ─────────────────────────────────────────────────────────────────────────────
# SHADOW EMBEDDER (Context Manager — Bellek Temizliği Garantili)
# ─────────────────────────────────────────────────────────────────────────────

class ShadowEmbedder:
    """
    Shadow model için izole embedder.
    Context manager kullanımı: belleği garantili temizler.

    Örnek:
        with ShadowEmbedder("shadow_mursit_large") as emb:
            vecs = emb.encode_batch(texts)
        # Model burada bellekten kaldırılmıştır
    """

    def __init__(self, model_key: str):
        self.cfg = get_model_config(model_key)
        self.model_key = model_key
        self._model: SentenceTransformer | None = None

        # Güvenlik: Production collection'ına asla yazma
        if is_production_collection(self.cfg["collection"]):
            raise RuntimeError(
                f"GÜVENLİK HATASI: shadow_encoder, production collection'ına "
                f"({self.cfg['collection']}) erişmeye çalışıyor! İşlem durduruldu."
            )

    def __enter__(self) -> "ShadowEmbedder":
        self._load()
        return self

    def __exit__(self, *_):
        self._unload()

    def _load(self):
        model_id = self.cfg.get("local_path") or self.cfg["model_id"]
        log.info(f"[ShadowEmbedder] Model yükleniyor: {model_id}")
        t0 = time.time()
        try:
            self._model = SentenceTransformer(
                model_id, device="cpu", local_files_only=True, trust_remote_code=True
            )
        except Exception:
            log.info("[ShadowEmbedder] Çevrimdışı bulunamadı, HuggingFace'den indiriliyor...")
            self._model = SentenceTransformer(
                model_id, device="cpu", trust_remote_code=True
            )
        self.vector_size = self._model.get_embedding_dimension()
        if hasattr(self._model, "max_seq_length") and self._model.max_seq_length:
            if self._model.max_seq_length > 512 and "Large" not in model_id:
                self._model.max_seq_length = 512
        log.info(f"[ShadowEmbedder] Hazır — {time.time()-t0:.1f}s | dim={self.vector_size}")

    def _unload(self):
        if self._model is not None:
            del self._model
            self._model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        log.info("[ShadowEmbedder] Model bellekten temizlendi.")

    def encode_batch(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        if self._model is None:
            raise RuntimeError("Model yüklü değil. Context manager kullanın.")
        prefix = self.cfg.get("query_prefix", "") or ""
        if prefix:
            texts = [prefix + t for t in texts]
        vecs = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs.tolist()

    def encode_single(self, text: str) -> list[float]:
        """Query encoding (query_prefix uygulanır)."""
        prefix = self.cfg.get("query_prefix", "") or ""
        full = prefix + text.strip()
        return self._model.encode(
            full,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).tolist()


# ─────────────────────────────────────────────────────────────────────────────
# CORPUS ENCODING
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_shadow_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    force_reset: bool = False,
) -> None:
    """Shadow collection'ı oluşturur ya da mevcut sayısını raporlar."""
    existing = [c.name for c in _qdrant_retry(client.get_collections).collections]

    if force_reset and collection_name in existing:
        _qdrant_retry(client.delete_collection, collection_name)
        log.info(f"[Collection] Silindi (force-reset): {collection_name}")
        existing.remove(collection_name)

    if collection_name not in existing:
        _qdrant_retry(
            client.create_collection,
            collection_name,
            vectors_config=qm.VectorParams(size=vector_size, distance=DISTANCE_METRIC),
        )
        log.info(f"[Collection] Oluşturuldu: {collection_name} (dim={vector_size})")
    else:
        count = _qdrant_retry(client.count, collection_name).count
        log.info(f"[Collection] Mevcut: {collection_name} ({count} nokta)")


def _get_encoded_ids(client: QdrantClient, collection_name: str, corpus: list[dict]) -> set[int]:
    """Zaten encode edilmiş chunk_id'leri döndürür (cache kontrolü)."""
    ids = [_chunk_id_to_uint64(c["chunk_id"]) for c in corpus]
    existing: set[int] = set()
    for i in range(0, len(ids), 1000):
        try:
            pts = _qdrant_retry(
                client.retrieve,
                collection_name=collection_name,
                ids=ids[i : i + 1000],
                with_payload=False,
                with_vectors=False,
            )
            existing.update(p.id for p in pts)
        except Exception as e:
            log.warning(f"[Cache] ID kontrolü hatası: {e}")
    return existing


def encode_shadow_corpus(
    model_key: str,
    force_re_encode: bool = False,
    test_mode: bool = False,
    batch_size: int = 16,
) -> None:
    """
    Corpus'u shadow modelin embedding'iyle encode edip ilgili Qdrant shadow
    collection'ına yazar.

    - Zaten encode edilmiş chunk'ları tekrar encode ETMEZ (cache kontrolü).
    - force_re_encode=True ise collection sıfırlanır ve tümden encode edilir.
    - test_mode=True ise sadece ilk 100 chunk encode edilir (hızlı doğrulama).
    - Production collection'ına ASLA yazmaz (güvenlik kontrolü aktif).
    """
    cfg = get_model_config(model_key)
    collection_name = cfg["collection"]

    # Çift güvenlik kontrolü
    if is_production_collection(collection_name):
        raise RuntimeError(
            f"GÜVENLIK HATASI: encode_shadow_corpus production collection'ına "
            f"({collection_name}) yazmaya çalışıyor! Durduruldu."
        )

    corpus = _load_corpus(test_mode=test_mode)
    client = get_qdrant_client()

    with ShadowEmbedder(model_key) as emb:
        _ensure_shadow_collection(
            client, collection_name, emb.vector_size, force_reset=force_re_encode
        )

        # Cache kontrolü
        if not force_re_encode:
            encoded_ids = _get_encoded_ids(client, collection_name, corpus)
            todo = [c for c in corpus if _chunk_id_to_uint64(c["chunk_id"]) not in encoded_ids]
        else:
            todo = corpus
            encoded_ids = set()

        log.info(
            f"Encode durumu: Toplam={len(corpus)} | "
            f"Mevcut={len(encoded_ids)} | Eklenecek={len(todo)}"
        )

        if not todo:
            log.info("Tüm chunk'lar zaten encode edilmiş. Atlanıyor.")
            return

        t0 = time.time()
        eklenen = 0
        for i in tqdm(
            range(0, len(todo), batch_size),
            desc=f"Shadow encode ({model_key})",
            total=(len(todo) + batch_size - 1) // batch_size,
        ):
            batch = todo[i : i + batch_size]
            texts = [_build_encode_text(c) for c in batch]
            vecs = emb.encode_batch(texts, batch_size=batch_size)

            points = [
                qm.PointStruct(
                    id=_chunk_id_to_uint64(c["chunk_id"]),
                    vector=vecs[idx],
                    payload={
                        "chunk_id": c.get("chunk_id", ""),
                        "text": c.get("text", ""),
                        "law": c.get("law", ""),
                        "article_no": c.get("article_no", ""),
                        "source": c.get("source", ""),
                        "decision_id": c.get("decision_id", ""),
                        "token_len": c.get("token_len", 0),
                        "atiflar": c.get("atiflar", []),
                    },
                )
                for idx, c in enumerate(batch)
            ]
            _qdrant_retry(client.upsert, collection_name=collection_name, points=points)
            eklenen += len(batch)

        elapsed = time.time() - t0
        log.info(
            f"[shadow_encoder] Tamamlandı. {eklenen} chunk encode edildi. "
            f"Süre: {elapsed:.1f}s ({elapsed/60:.1f} dk) | Collection: {collection_name}"
        )


def cleanup_shadow_collection(model_key: str, dry_run: bool = False) -> None:
    """Shadow Qdrant collection'ını siler (disk alanı için opsiyonel)."""
    cfg = get_model_config(model_key)
    collection_name = cfg["collection"]

    if is_production_collection(collection_name):
        raise RuntimeError(
            f"GÜVENLIK HATASI: cleanup_shadow_collection production collection'ını "
            f"({collection_name}) silmeye çalışıyor! Durduruldu."
        )

    client = get_qdrant_client()
    existing = [c.name for c in _qdrant_retry(client.get_collections).collections]

    if collection_name not in existing:
        log.info(f"[Cleanup] Collection zaten mevcut değil: {collection_name}")
        return

    count = _qdrant_retry(client.count, collection_name).count
    if dry_run:
        log.info(f"[Cleanup] DRY RUN — Silinecek: {collection_name} ({count} nokta)")
        return

    _qdrant_retry(client.delete_collection, collection_name)
    log.info(f"[Cleanup] Silindi: {collection_name} ({count} nokta kaldırıldı)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LawAgent Shadow Corpus Encoder — Production'a dokunmadan shadow eval"
    )
    parser.add_argument(
        "--model-key",
        required=True,
        choices=list_shadow_models() + ["shadow_mursit_large", "shadow_turk4retrieval", "shadow_bge_m3"],
        help="Registry'deki shadow model anahtarı",
    )
    parser.add_argument(
        "--force-re-encode",
        action="store_true",
        help="Collection'ı sıfırla ve tümden encode et (cache'i yok say)",
    )
    parser.add_argument(
        "--test-encode",
        action="store_true",
        help="Sadece ilk 100 chunk encode et (hızlı doğrulama)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Encoding batch boyutu (varsayılan: 16)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Shadow Qdrant collection'ını sil (disk alanı için)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="--cleanup için: silmeden önce ne silineceğini göster",
    )
    args = parser.parse_args()

    if args.cleanup:
        cleanup_shadow_collection(args.model_key, dry_run=args.dry_run)
    else:
        encode_shadow_corpus(
            model_key=args.model_key,
            force_re_encode=args.force_re_encode,
            test_mode=args.test_encode,
            batch_size=args.batch_size,
        )
