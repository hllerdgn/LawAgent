"""
shadow_retriever.py  —  LawAgent Shadow Model Retriever
========================================================

Production LegalRetriever'dan TAMAMEN BAĞIMSIZ, shadow modeller için
mini retriever. Production serving path'ine (retriever.py, generator.py)
hiç dokunmaz.

Kullanım eval_v2.py'den:
    from shadow_retriever import ShadowRetriever
    with ShadowRetriever("shadow_mursit_large") as ret:
        chunks = ret.retrieve(query, k=10)
"""

from __future__ import annotations

import gc
import json
import logging
import math
import os
import sys
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

# Proje dizin yapısı
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)

for _p in [_SRC_DIR, _BACKEND_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
for _env in [
    os.path.join(_BACKEND_DIR, ".env"),
    os.path.join(_BACKEND_DIR, "src", ".env"),
]:
    if os.path.exists(_env):
        load_dotenv(dotenv_path=_env)
        break

import torch

from config.embedding_models import get_model_config, is_production_collection
from shadow_encoder import ShadowEmbedder, encode_shadow_corpus
from services.qdrant_client import get_qdrant_client
from qdrant_client.http import models as qm

# Production modüllerini import et (sadece yardımcı fonksiyonlar — saf Python)
from retriever import (
    BM25Plus,
    hybrid_fuse,
    _apply_diversity_penalty,
    _minmax_normalize,
    expand_query,
    _clean_query,
    detect_kanun_probs,
    extract_madde,
    normalize_article,
    _KEYWORD_TO_ARTICLE,
    CFG,
)

log = logging.getLogger("LawAgent.ShadowRetriever")

_DATA_DIR = os.path.join(_SRC_DIR, "data")
ENRICHED_CORPUS = os.path.join(_DATA_DIR, "chunk_corpus_enriched.json")
CHUNK_CORPUS = os.path.join(_DATA_DIR, "chunk_corpus.json")


def _chunk_id_to_uint64(cid: str) -> int:
    return uuid.uuid5(uuid.NAMESPACE_DNS, str(cid)).int >> 64


def _qdrant_retry(func, *args, retries: int = 4, delay: float = 0.8, **kwargs):
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(delay * (2 ** i))


# ─────────────────────────────────────────────────────────────────────────────
# SHADOW RETRIEVER
# ─────────────────────────────────────────────────────────────────────────────

class ShadowRetriever:
    """
    Shadow model için tam izole retriever.
    Production collection'ına asla erişmez.

    Context manager:
        with ShadowRetriever("shadow_mursit_large") as ret:
            results = ret.retrieve("sorgu metni", k=10)
    """

    def __init__(
        self,
        model_key: str,
        auto_encode: bool = True,
        force_re_encode: bool = False,
    ):
        self.model_key = model_key
        self.cfg = get_model_config(model_key)
        self._embedder: ShadowEmbedder | None = None
        self._bm25: BM25Plus | None = None
        self._corpus: list[dict] | None = None
        self._qdrant = None
        self.auto_encode = auto_encode
        self.force_re_encode = force_re_encode

        # Güvenlik kontrolü
        if is_production_collection(self.cfg["collection"]):
            raise RuntimeError(
                f"GÜVENLIK HATASI: ShadowRetriever production collection'ı "
                f"({self.cfg['collection']}) için çağrılamaz!"
            )

    def __enter__(self) -> "ShadowRetriever":
        self._init()
        return self

    def __exit__(self, *_):
        self.close()

    def _init(self) -> None:
        log.info(f"[ShadowRetriever] Başlatılıyor: {self.model_key}")

        # 1. Corpus yükle (BM25 için)
        corpus_path = ENRICHED_CORPUS if os.path.exists(ENRICHED_CORPUS) else CHUNK_CORPUS
        with open(corpus_path, "r", encoding="utf-8") as f:
            self._corpus = json.load(f)
        log.info(f"[ShadowRetriever] Corpus yüklendi: {len(self._corpus)} chunk")

        # 2. BM25 indexi oluştur
        log.info("[ShadowRetriever] BM25+ indexi hazırlanıyor...")
        t0 = time.time()
        self._bm25 = BM25Plus()
        texts = []
        for c in self._corpus:
            if c.get("source") == "yargitay":
                texts.append(f"Yargıtay Kararı {c.get('decision_id', '')}: {c.get('text', '')}")
            else:
                texts.append(
                    f"{c.get('law', '')} Madde {c.get('article_no', '')}: {c.get('text', '')}"
                )
        self._bm25.index(texts)
        log.info(f"[ShadowRetriever] BM25+ hazır — {time.time()-t0:.1f}s")

        # 3. Shadow Qdrant collection kontrol et, yoksa encode et
        self._qdrant = get_qdrant_client()
        existing_colls = [c.name for c in _qdrant_retry(self._qdrant.get_collections).collections]
        collection = self.cfg["collection"]

        if collection not in existing_colls or self.force_re_encode:
            if self.auto_encode:
                log.info(
                    f"[ShadowRetriever] Shadow collection bulunamadı ({collection}), "
                    f"encode_shadow_corpus başlatılıyor..."
                )
                encode_shadow_corpus(
                    self.model_key,
                    force_re_encode=self.force_re_encode,
                )
            else:
                raise RuntimeError(
                    f"Shadow collection '{collection}' Qdrant'ta mevcut değil. "
                    f"Önce: python src/shadow_encoder.py --model-key {self.model_key}"
                )
        else:
            count = _qdrant_retry(self._qdrant.count, collection).count
            log.info(f"[ShadowRetriever] Shadow collection mevcut: {collection} ({count} nokta)")

        # 4. Shadow embedder yükle (sadece query encoding için)
        self._embedder = ShadowEmbedder(self.model_key)
        self._embedder._load()
        log.info(f"[ShadowRetriever] Hazır — {self.model_key}")

    def close(self) -> None:
        """Belleği temizle."""
        if self._embedder is not None:
            self._embedder._unload()
            self._embedder = None
        self._bm25 = None
        self._corpus = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        log.info(f"[ShadowRetriever] Kapatıldı: {self.model_key}")

    # ── Dense Search ─────────────────────────────────────────────────────────

    def _dense_search(self, query: str, k: int = 200) -> list[dict]:
        vec = self._embedder.encode_single(query)
        res = _qdrant_retry(
            self._qdrant.query_points,
            collection_name=self.cfg["collection"],
            query=vec,
            limit=k,
            with_payload=True,
        )
        hits = res.points if hasattr(res, "points") else res
        results = []
        for h in hits:
            payload = h.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id", str(h.id)),
                "text": payload.get("text", ""),
                "law": payload.get("law", ""),
                "article_no": payload.get("article_no", ""),
                "source": payload.get("source", ""),
                "decision_id": payload.get("decision_id", ""),
                "token_len": payload.get("token_len", 0),
                "atiflar": payload.get("atiflar", []),
                "dense_score": float(h.score),
                "bm25_score": 0.0,
            })
        return results

    # ── BM25 Search ──────────────────────────────────────────────────────────

    def _bm25_search(self, query: str, k: int = 200) -> list[dict]:
        hits = self._bm25.score(query, n=k)
        results = []
        for idx, score in hits:
            c = self._corpus[idx]
            results.append({
                "chunk_id": c.get("chunk_id", ""),
                "text": c.get("text", ""),
                "law": c.get("law", ""),
                "article_no": c.get("article_no", ""),
                "source": c.get("source", ""),
                "decision_id": c.get("decision_id", ""),
                "token_len": c.get("token_len", 0),
                "atiflar": c.get("atiflar", []),
                "dense_score": 0.0,
                "bm25_score": score,
            })
        return results

    # ── Article Boost ─────────────────────────────────────────────────────────

    def _apply_article_boost(
        self, fused: list[dict], query: str
    ) -> list[dict]:
        """Production ile aynı _KEYWORD_TO_ARTICLE boost mantığı."""
        q_lower = query.lower()
        boost_targets: list[tuple[str, str, float]] = []

        for patterns, (target_law, target_article) in _KEYWORD_TO_ARTICLE:
            if all(p in q_lower for p in patterns):
                boost_targets.append((target_law, target_article, CFG.BOOST_MADDE))

        kanun_probs = detect_kanun_probs(query)
        if kanun_probs:
            top_kanun = max(kanun_probs, key=kanun_probs.get)
            top_prob = kanun_probs[top_kanun]
            if top_prob > 0.5:
                for c in fused:
                    if c.get("law", "").upper() == top_kanun.upper():
                        c["skor"] = c.get("skor", 0) + CFG.BOOST_KANUN * top_prob * 0.1

        madde_no = extract_madde(query)
        for law_key, art_key, boost_val in boost_targets:
            for c in fused:
                if (
                    c.get("law", "").upper() == law_key.upper()
                    and normalize_article(c.get("article_no")) == normalize_article(art_key)
                ):
                    c["skor"] = c.get("skor", 0) + boost_val

        if madde_no:
            for law_key, prob in kanun_probs.items():
                for c in fused:
                    if (
                        c.get("law", "").upper() == law_key.upper()
                        and normalize_article(c.get("article_no")) == madde_no
                    ):
                        c["skor"] = c.get("skor", 0) + CFG.BOOST_MADDE * prob

        fused.sort(key=lambda x: -x.get("skor", 0))
        return fused

    # ── Filter (Max Same Article) ─────────────────────────────────────────────

    def _filter_results(self, fused: list[dict], k: int) -> list[dict]:
        seen_articles: dict[str, int] = defaultdict(int)
        out = []
        for c in fused:
            law = c.get("law", "")
            art = normalize_article(c.get("article_no"))
            key = f"{law}_{art}" if art else c.get("chunk_id", "")
            if seen_articles[key] >= CFG.MAX_SAME_ARTICLE:
                continue
            seen_articles[key] += 1
            out.append(c)
            if len(out) >= k:
                break
        return out

    # ── Alpha Selection ───────────────────────────────────────────────────────

    def _choose_alpha(self, query: str) -> float:
        q_lower = query.lower()
        kanun_probs = detect_kanun_probs(query)
        if kanun_probs:
            top_prob = max(kanun_probs.values())
            if top_prob > 0.75:
                return CFG.ALPHA_SEMANTIC
        madde_no = extract_madde(query)
        if madde_no:
            return CFG.ALPHA_EXACT
        return CFG.ALPHA_DEFAULT

    # ── Main Retrieve ─────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        k: int = 10,
        query_category: Optional[str] = None,
    ) -> list[dict]:
        """
        Shadow model ile retrieval yapar. Production pipeline ile aynı
        BM25+Dense fusion mantığını kullanır; TKHK reranker kapalı
        (saf embedding kalitesi ölçülür).

        Returns: k adet chunk dict (skor, law, article_no, text, ...)
        """
        if not self._embedder or not self._bm25:
            raise RuntimeError("ShadowRetriever başlatılmamış. Context manager kullanın.")

        t0 = time.time()

        # 1. Sorgu temizle + genişlet
        clean_q = _clean_query(query)
        expanded_q = expand_query(clean_q)

        # 2. Dense + BM25 arama
        dense_hits = self._dense_search(expanded_q, k=CFG.TOP_K_DENSE)
        bm25_hits = self._bm25_search(expanded_q, k=CFG.TOP_K_BM25)

        if not dense_hits and not bm25_hits:
            log.warning(f"[ShadowRetriever] Sonuç bulunamadı: '{query[:50]}'")
            return []

        # 3. Hybrid fusion
        alpha = self._choose_alpha(clean_q)
        fused = hybrid_fuse(dense_hits, bm25_hits, alpha=alpha)

        # 4. Article boost
        fused = self._apply_article_boost(fused, clean_q)

        # 5. Diversity penalty
        fused = _apply_diversity_penalty(fused, penalty=CFG.DIVERSITY_PENALTY)

        # NOT: TKHK reranker kasıtlı olarak KAPALI — saf embedding kalitesini ölçüyoruz
        # Reranker etkisini ayrı değerlendirmek için bu yeterlidir.

        # 6. Filtrele
        result = self._filter_results(fused, k=k)

        elapsed_ms = (time.time() - t0) * 1000
        log.debug(
            f"[ShadowRetriever] '{query[:40]}' → {len(result)} sonuç | "
            f"{elapsed_ms:.0f}ms | α={alpha:.2f}"
        )
        return result
