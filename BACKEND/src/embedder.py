"""
embedder.py  —  LawAgent Mursit Embedder API
"""

import argparse
import json
import os
import sys
import time
import uuid
import logging
from pathlib import Path

# services/ klasörü BACKEND/ kökünde — hangi dizinden çalıştırılırsa çalıştırılsın bulsun
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# .env dosyasını yükle (QDRANT_URL, GROQ_API_KEY vs. için)
from dotenv import load_dotenv
for _env_path in [
    Path(_BACKEND_DIR) / ".env",
    Path(_BACKEND_DIR).parent / ".env",
]:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
        print(f"[Embedder] .env yüklendi: {_env_path}")
        break

import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from services.qdrant_client import get_qdrant_client

# Logging Yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.Embedder")

# tqdm Entegrasyonu (Yüklü değilse fallback fonksiyonu çalışır)
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=None, total=None, **kwargs):
        log.info(f"{desc or 'İşlem yapılıyor'}...")
        return iterable

# Yollar ve Sabitler
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_NAME = "newmindai/Mursit-Base-TR-Retrieval"
COLLECTION_NAME = "lawagent_mursit"

# Eğer zenginleştirilmiş corpus varsa öncelikli olarak onu kullan
ENRICHED_CORPUS = os.path.join(DATA_DIR, "chunk_corpus_enriched.json")
if os.path.exists(ENRICHED_CORPUS):
    CHUNK_CORPUS = ENRICHED_CORPUS
else:
    CHUNK_CORPUS = os.path.join(DATA_DIR, "chunk_corpus.json")

QUANTIZE_PATH = os.path.join(DATA_DIR, "mursit_int8.pt")
DISTANCE_METRIC = qmodels.Distance.COSINE


# ═══════════════════════════════════════════════════════════════════════════════
# AĞ TOLERANSI (QDRANT RETRY YARDIMCISI)
# ═══════════════════════════════════════════════════════════════════════════════

def qdrant_retry(func, *args, retries: int = 5, delay: float = 1.0, **kwargs):
    """Qdrant işlemleri sırasında oluşabilecek ağ kesintilerine karşı üstel geri çekilmeli retry mekanizması."""
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == retries - 1:
                raise e
            wait_time = delay * (2 ** i)
            log.warning(f"Qdrant sorgu hatası (Deneme {i+1}/{retries}): {e}. {wait_time}s bekleniyor...")
            time.sleep(wait_time)


# ═══════════════════════════════════════════════════════════════════════════════
# MURSIT EMBEDDER SINIFI
# ═══════════════════════════════════════════════════════════════════════════════

class MursitEmbedder:
    """
    Mursit-Base-TR-Retrieval için embedding sınıfı.
    GPU ivmelendirme (CUDA/MPS) ve CPU kuantizasyon yönetimi içerir.

    Parametreler:
        quantize          : int8 dynamic quantization (sadece CPU)
        device            : 'cpu' | 'cuda' | 'mps' | None (otomatik)
        model_name_or_path: HuggingFace model adı veya yerel klasör yolu.
                            None ise MODEL_NAME sabiti kullanılır.
                            Fine-tuned checkpoint'ler için kullanın.
    """

    def __init__(
        self,
        quantize: bool = False,
        device: str = None,
        model_name_or_path: str = None,
    ):
        self.quantize = quantize
        _model_id = model_name_or_path if model_name_or_path else MODEL_NAME

        # Cihaz Otomatik Algılama
        if quantize:
            self.device = "cpu"
            if device and device != "cpu":
                log.warning("Kuantizasyon sadece CPU üzerinde desteklenir. Cihaz 'cpu' olarak zorlandı.")
        else:
            if device:
                self.device = device
            else:
                if torch.cuda.is_available():
                    self.device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.device = "mps"
                else:
                    self.device = "cpu"

        log.info(
            f"[Mursit] Model yükleniyor ({self.device} - {'int8' if quantize else 'float32'})..."
            f"  model={_model_id}"
        )
        t0 = time.time()

        try:
            self.st = SentenceTransformer(_model_id, device=self.device, local_files_only=True)
        except Exception as e:
            log.warning(f"Çevrimdışı model yükleme başarısız ({e}), çevrimiçi deneniyor...")
            self.st = SentenceTransformer(_model_id, device=self.device)
        
        self.vector_size = self.st.get_embedding_dimension()

        if quantize:
            self._load_or_quantize()

        log.info(f"[Mursit] Hazır — {time.time()-t0:.1f}s | dim={self.vector_size}")

    def _load_or_quantize(self) -> None:
        transformer_module = self.st._first_module().auto_model

        quantized = torch.quantization.quantize_dynamic(
            transformer_module, {torch.nn.Linear}, dtype=torch.qint8
        )

        if os.path.exists(QUANTIZE_PATH):
            log.info("Kaydedilmiş int8 ağırlıklar yükleniyor...")
            try:
                state = torch.load(QUANTIZE_PATH, map_location="cpu")
                quantized.load_state_dict(state)
            except Exception as e:
                log.warning(f"Kaydedilmiş int8 yüklenemedi, sıfırdan kuantize ediliyor: {e}")
        else:
            log.info("Model dinamik olarak kuantize ediliyor (ilk kez)...")
            os.makedirs(os.path.dirname(QUANTIZE_PATH) or ".", exist_ok=True)
            torch.save(quantized.state_dict(), QUANTIZE_PATH)
            log.info(f"int8 ağırlıklar kaydedildi -> {QUANTIZE_PATH}")

        self.st._first_module().auto_model = quantized

    def encode(self, texts: list[str], batch_size: int = 32, normalize: bool = True) -> list:
        """Liste halindeki metinleri vektöre çevirir (Python list of list[float])."""
        return self.st.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            batch_size=batch_size,
        ).tolist()

    def encode_single(self, text: str, normalize: bool = True) -> list[float]:
        """Arama sorgusunu Mürşit modeline uygun prefix ile vektöre çevirir."""
        prefix = "query: "
        full_text = prefix + text.strip()
        
        return self.st.encode(
            full_text, 
            normalize_embeddings=normalize,
            show_progress_bar=False,
            convert_to_numpy=True 
        ).tolist()

    def kaydet(self, yol: str = QUANTIZE_PATH) -> None:
        if not self.quantize:
            log.warning("float32 model kaydedilmiyor. Lütfen --quantize ile çalıştırın.")
            return
        os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
        torch.save(self.st._first_module().auto_model.state_dict(), yol)
        mb = os.path.getsize(yol) / 1024 / 1024
        log.info(f"int8 kaydedildi -> {yol} ({mb:.1f} MB)")


# ═══════════════════════════════════════════════════════════════════════════════
# QDRANT YARDIMCI FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════════════════════

def _chunk_id_to_uint64(cid: str) -> int:
    return uuid.uuid5(uuid.NAMESPACE_DNS, str(cid)).int >> 64


def _get_existing_ids(client: QdrantClient, corpus: list) -> set:
    ids = [_chunk_id_to_uint64(c["chunk_id"]) for c in corpus]
    existing = set()
    for i in range(0, len(ids), 1000):
        try:
            points = qdrant_retry(
                client.retrieve,
                collection_name=COLLECTION_NAME,
                ids=ids[i : i + 1000],
                with_payload=False,
                with_vectors=False,
            )
            existing.update(p.id for p in points)
        except Exception as e:
            log.warning(f"Qdrant'tan mevcut ID'ler çekilirken hata oluştu: {e}")
    return existing


def _ensure_collection(client: QdrantClient, vector_size: int, reset: bool) -> None:
    collections_res = qdrant_retry(client.get_collections)
    existing = [c.name for c in collections_res.collections]
    
    if reset and COLLECTION_NAME in existing:
        qdrant_retry(client.delete_collection, COLLECTION_NAME)
        log.info(f"Collection silindi: {COLLECTION_NAME}")
        existing.remove(COLLECTION_NAME)
        
    if COLLECTION_NAME not in existing:
        qdrant_retry(
            client.create_collection,
            COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=vector_size, distance=DISTANCE_METRIC
            ),
        )
        log.info(f"Collection oluşturuldu: {COLLECTION_NAME}")
    else:
        count = qdrant_retry(client.count, COLLECTION_NAME).count
        log.info(f"Collection mevcut: {COLLECTION_NAME} ({count} kayıt)")


# ═══════════════════════════════════════════════════════════════════════════════
# VERİ TABANI OLUŞTURMA (EMBED CORPUS)
# ═══════════════════════════════════════════════════════════════════════════════

def embed_corpus(
    reset: bool = False,
    test_mode: bool = False,
    quantize: bool = False,
    batch_size: int = 32,
    device: str = None,
) -> None:
    if not os.path.exists(CHUNK_CORPUS):
        log.error(f"{CHUNK_CORPUS} bulunamadı. Önce legal_chunker.py çalıştırılmalı.")
        return

    with open(CHUNK_CORPUS, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    if test_mode:
        corpus = corpus[:20]
        log.info("Test modu aktif: Sadece ilk 20 chunk işlenecek.")

    embedder = MursitEmbedder(quantize=quantize, device=device)
    client = get_qdrant_client()

    _ensure_collection(client, embedder.vector_size, reset)

    existing = set() if reset else _get_existing_ids(client, corpus)
    yeni = [c for c in corpus if _chunk_id_to_uint64(c["chunk_id"]) not in existing]
    
    log.info(f"Veri Durumu: Toplam={len(corpus)} | Mevcut={len(existing)} | Eklenecek={len(yeni)}")
    if not yeni:
        log.info("Tüm veriler güncel. Eklenecek yeni chunk yok.")
        return

    t0 = time.time()
    eklenen = 0
    toplam = len(yeni)

    for i in tqdm(range(0, toplam, batch_size), desc="Vektörleştirme ve Yükleme", total=(toplam + batch_size - 1) // batch_size):
        batch = yeni[i : i + batch_size]
        enriched_texts = []
        for c in batch:
            source = c.get("source", "")
            text = c.get("text", "")

            if source == "yargitay":
                enriched_texts.append(f"Yargıtay Kararı {c.get('decision_id', '')}: {text}")
            else:
                enriched_texts.append(f"{c.get('law', '')} Madde {c.get('article_no', '')}: {text}")

        # Vektörleri hesapla
        vecs = embedder.encode(enriched_texts, batch_size=batch_size)

        points = [
            qmodels.PointStruct(
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
                    "atiflar": c.get("atiflar", [])
                },
            )
            for idx, c in enumerate(batch)
        ]
        
        # Qdrant'a yükle (Retry korumalı)
        qdrant_retry(client.upsert, collection_name=COLLECTION_NAME, points=points)
        eklenen += len(batch)

    # CUDA bellek temizliği
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    log.info(f"Tamamlandı. {eklenen} chunk başarıyla yüklendi. (Süre: {time.time()-t0:.1f}s)")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI GİRİŞİ
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LawAgent Mursit Embedder v11 (GPU & Retry & tqdm)")
    parser.add_argument("--reset", action="store_true", help="Collection'ı sıfırla ve baştan başla")
    parser.add_argument("--test", action="store_true", help="Sadece ilk 20 chunk ile test et")
    parser.add_argument("--quantize", action="store_true", help="int8 dinamik kuantizasyon")
    parser.add_argument("--kaydet", action="store_true", help="Kuantize modeli kaydet")
    parser.add_argument("--batch-size", type=int, default=32, help="Encoding batch boyutu (varsayılan: 32)")
    parser.add_argument("--device", type=str, default=None, help="Cihaz zorla (cpu, cuda, mps vb.)")
    args = parser.parse_args()

    if args.kaydet:
        embedder = MursitEmbedder(quantize=args.quantize, device=args.device)
        embedder.kaydet()
    else:
        embed_corpus(
            reset=args.reset,
            test_mode=args.test,
            quantize=args.quantize,
            batch_size=args.batch_size,
            device=args.device,
        )
