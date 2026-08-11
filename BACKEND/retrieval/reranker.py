"""
retrieval/reranker.py  —  LawAgent Cross-Encoder Reranker
===========================================================

Sorumluluklar:
  - CrossEncoder modelini yüklemek (lazy, ilk kullanımda)
  - Query-document pair oluşturmak (metadata-rich format)
  - Her çift için cross-attention skoru hesaplamak
  - Adayları yeniden sıralamak
  - Latency (gecikme) ölçümü ve loglama

Kullanım:
  from retrieval.reranker import CrossEncoderReranker, RerankerConfig

  cfg = RerankerConfig(model="BAAI/bge-reranker-base", top_k=30)
  reranker = CrossEncoderReranker(cfg)
  reranked_chunks = reranker.rerank(query, candidate_chunks)

Model Önceliği:
  1. BAAI/bge-reranker-base          (~270MB, çok dilli, Türkçe-uyumlu)
  2. cross-encoder/ms-marco-MiniLM-L-6-v2  (~90MB, fallback, İngilizce ağırlıklı)

Etkinleştirme:
  ENABLE_CROSS_RERANK=true (ortam değişkeni)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger("LawAgent.Reranker")


# ═══════════════════════════════════════════════════════════════════════════════
# KONFİGÜRASYON
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RerankerConfig:
    """
    CrossEncoderReranker için yapılandırma parametreleri.

    Attributes:
        model: Öncelikli cross-encoder model adı (HuggingFace Hub veya yerel yol).
        fallback_models: Birincil model yüklenemezse sırayla denenen yedek modeller.
        top_k: Yeniden sıralanacak aday sayısı (tüm corpus'a asla uygulanmaz).
        max_doc_chars: Document metninin cross-encoder'a gönderilecek maksimum karakter sayısı.
        device: Model çalışma cihazı ("cpu", "cuda", "mps" veya None=otomatik).
        batch_size: CrossEncoder.predict() için batch boyutu.
    """

    model: str = "BAAI/bge-reranker-base"
    fallback_models: List[str] = field(
        default_factory=lambda: ["cross-encoder/ms-marco-MiniLM-L-6-v2"]
    )
    top_k: int = 30
    max_doc_chars: int = 512
    device: Optional[str] = "cpu"
    batch_size: int = 16


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT FORMAT YARDIMCISI
# ═══════════════════════════════════════════════════════════════════════════════


def _build_document_text(chunk: Dict, max_chars: int = 512) -> str:
    """
    Chunk sözlüğünden cross-encoder'a gönderilecek yapılandırılmış belge metni oluşturur.

    Format (metadata + içerik):
        Kanun:
        TBK

        Madde:
        117

        Kaynak:
        Mevzuat

        Metin:
        Borçlu temerrüde düşmüş ise...

    Bu format cross-encoder'ın kanun, madde ve kaynak bilgisini bağlamsal olarak
    değerlendirmesini sağlar; salt düz metne kıyasla daha yüksek skorlama doğruluğu sunar.

    Args:
        chunk: Retriever'dan gelen metadata + metin içeren sözlük.
        max_chars: Metin alanının kırpılacağı maksimum karakter sayısı.

    Returns:
        Yapılandırılmış belge string'i.
    """
    law = (chunk.get("law") or "").strip()
    article_no = (chunk.get("article_no") or "").strip()
    source = (chunk.get("source") or "").strip()
    text = (chunk.get("text") or chunk.get("context_prefix") or "").strip()

    # Metni kırp (cross-encoder max token limitini aşmamak için)
    text_snippet = text[:max_chars]
    if len(text) > max_chars:
        text_snippet += "..."

    # Kaynak tipini Türkçe etiketle
    source_label_map = {
        "mevzuat": "Mevzuat",
        "yargitay": "Yargıtay İçtihadı",
        "site_document": "Belge",
    }
    source_label = source_label_map.get(source.lower(), source.capitalize())

    parts: List[str] = []

    if law:
        parts.append(f"Kanun:\n{law}")

    if article_no:
        parts.append(f"Madde:\n{article_no}")

    if source_label:
        parts.append(f"Kaynak:\n{source_label}")

    # Yargıtay kararları için ek metadata
    decision_id = (chunk.get("decision_id") or "").strip()
    if decision_id and source.lower() == "yargitay":
        parts.append(f"Karar No:\n{decision_id}")

    parts.append(f"Metin:\n{text_snippet}")

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-ENCODER RERANKER SINIFI
# ═══════════════════════════════════════════════════════════════════════════════


class CrossEncoderReranker:
    """
    LawAgent için Cross-Encoder tabanlı yeniden sıralayıcı.

    Çalışma Prensibi:
        Hybrid fusion ve boosting katmanından geçen Top-K adayı alır.
        Her (query, document) çifti için cross-attention skoru hesaplar.
        Adayları bu skora göre yeniden sıralar ve Top-K döndürür.

    Mimari Konumu:
        Dense + BM25 → Fusion → Boosting → [CrossEncoderReranker] → Final Filter

    Not:
        Model lazy yüklenir: ilk rerank() çağrısında yüklenir, sonraki çağrılarda önbellekten kullanılır.
        Model yüklenemezse (MemoryError, OS Error 1455 vb.) orijinal sıralama korunur.
    """

    def __init__(self, config: Optional[RerankerConfig] = None) -> None:
        """
        CrossEncoderReranker'ı başlatır.

        Args:
            config: RerankerConfig nesnesi. None ise varsayılan değerler kullanılır.
        """
        self.cfg = config or RerankerConfig()
        self._model = None          # Lazy yükleme: ilk rerank() çağrısında yüklenir
        self._model_name: Optional[str] = None
        self._load_attempted: bool = False

        log.info(
            f"[Reranker] Başlatıldı | Model: {self.cfg.model} | "
            f"top_k={self.cfg.top_k} | device={self.cfg.device}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Dahili: Model Yükleme
    # ──────────────────────────────────────────────────────────────────────────

    def _load_model(self) -> bool:
        """
        CrossEncoder modelini yükler. Birincil model başarısız olursa yedek modelleri dener.

        Model önceliği (RerankerConfig.model, ardından RerankerConfig.fallback_models):
            1. BAAI/bge-reranker-base  (~270MB, çok dilli, Türkçe hukuk metinleri için önerilir)
            2. cross-encoder/ms-marco-MiniLM-L-6-v2  (~90MB, fallback, İngilizce ağırlıklı)

        Returns:
            True: Model başarıyla yüklendi.
            False: Hiçbir model yüklenemedi.
        """
        if self._load_attempted and self._model is None:
            # Önceki yükleme girişimi başarısız — tekrar deneme
            self._load_attempted = False

        if self._load_attempted:
            return self._model is not None

        self._load_attempted = True

        candidates = [self.cfg.model] + list(self.cfg.fallback_models)

        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            log.error(
                "[Reranker] sentence-transformers yüklü değil. "
                "`pip install sentence-transformers` ile kurun."
            )
            return False

        for model_name in candidates:
            t_start = time.perf_counter()
            try:
                log.info(f"[Reranker] Yükleniyor: {model_name} (device={self.cfg.device})...")
                self._model = CrossEncoder(
                    model_name,
                    device=self.cfg.device,
                    max_length=512,
                )
                self._model_name = model_name
                elapsed = time.perf_counter() - t_start
                log.info(f"[Reranker] Yüklendi: {model_name} — {elapsed:.2f}s")
                return True

            except MemoryError:
                log.warning(
                    f"[Reranker] {model_name} — MemoryError (RAM yetersiz), "
                    "sonraki model deneniyor..."
                )
            except OSError as e:
                if "1455" in str(e):
                    log.warning(
                        f"[Reranker] {model_name} — OS Error 1455 (pagefile yetersiz), "
                        "sonraki model deneniyor..."
                    )
                else:
                    log.warning(f"[Reranker] {model_name} — OSError: {e}, sonraki model deneniyor...")
            except Exception as e:
                log.warning(
                    f"[Reranker] {model_name} — Yüklenemedi: {type(e).__name__}: {e}, "
                    "sonraki model deneniyor..."
                )

        log.error(
            "[Reranker] Hiçbir cross-encoder modeli yüklenemedi. "
            "Orijinal sıralama korunacak."
        )
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # Dahili: Pair Oluşturma
    # ──────────────────────────────────────────────────────────────────────────

    def _build_pairs(self, query: str, chunks: List[Dict]) -> List[tuple]:
        """
        (query, document_text) çiftleri oluşturur.

        Her doküman metni _build_document_text() ile kanun/madde/kaynak/metin
        alanlarını içeren yapılandırılmış formata dönüştürülür.

        Args:
            query: Kullanıcı sorgusu.
            chunks: Aday doküman listesi (her biri dict).

        Returns:
            CrossEncoder.predict() için (str, str) tuple listesi.
        """
        return [
            (query, _build_document_text(c, max_chars=self.cfg.max_doc_chars))
            for c in chunks
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Ana Metot: rerank()
    # ──────────────────────────────────────────────────────────────────────────

    def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Adayları cross-encoder skorlarına göre yeniden sıralar.

        Akış:
            1. İlk top_k aday alınır (tüm corpus'a ASLA uygulanmaz).
            2. (query, doc) çiftleri oluşturulur (metadata-rich format).
            3. CrossEncoder.predict() ile her çift için skor hesaplanır.
            4. Adaylar skora göre azalan sırada yeniden sıralanır.
            5. "cross_score" key'i her chunk'a eklenir (şeffaflık için).
            6. Sıralama dışı kalan adaylar (top_k sonrası) mevcut sıralamada korunur.

        Args:
            query: Kullanıcı sorgusu (Türkçe hukuki soru).
            chunks: Fusion + boosting katmanından geçmiş aday listesi.
                    En fazla self.cfg.top_k adayı değerlendirilir.

        Returns:
            Yeniden sıralanmış chunk listesi. Model yüklenemez veya hata oluşursa
            orijinal sıralama değiştirilmeden döndürülür.
        """
        if not chunks:
            return chunks

        # Model yükle (lazy)
        if self._model is None:
            loaded = self._load_model()
            if not loaded:
                log.warning("[Reranker] Model yok — orijinal sıralama korunuyor.")
                return chunks

        # Yalnızca ilk top_k aday değerlendirilir
        candidates: List[Dict] = chunks[: self.cfg.top_k]
        tail: List[Dict] = chunks[self.cfg.top_k :]

        # ── Latency: Pair oluşturma ───────────────────────────────────────────
        t_pair_start = time.perf_counter()
        pairs = self._build_pairs(query, candidates)
        t_pair_elapsed = time.perf_counter() - t_pair_start

        # ── Latency: Scoring (cross-encoder forward pass) ─────────────────────
        t_score_start = time.perf_counter()
        try:
            scores = self._model.predict(
                pairs,
                batch_size=self.cfg.batch_size,
                show_progress_bar=False,
            )
        except Exception as e:
            log.warning(
                f"[Reranker] Scoring hatası: {type(e).__name__}: {e}. "
                "Orijinal sıralama korunuyor."
            )
            # OS Error 1455 / Memory hatalarında modeli sıfırla — bir sonraki çağrıda yeniden yüklensin
            if "1455" in str(e) or "memory" in str(e).lower():
                log.warning("[Reranker] Bellek hatası tespit edildi — model sıfırlanıyor.")
                self._model = None
                self._model_name = None
                self._load_attempted = False
            return chunks

        t_score_elapsed = time.perf_counter() - t_score_start
        t_total_elapsed = t_pair_elapsed + t_score_elapsed

        # ── Skoru her chunk'a yaz ─────────────────────────────────────────────
        for chunk, score in zip(candidates, scores):
            chunk["cross_score"] = float(score)

        # ── Azalan skora göre sırala ──────────────────────────────────────────
        reranked = sorted(candidates, key=lambda x: x.get("cross_score", 0.0), reverse=True)

        # ── Loglama ───────────────────────────────────────────────────────────
        top1 = reranked[0] if reranked else {}
        log.info(
            f"[Reranker] {len(candidates)} aday yeniden sıralandı | "
            f"Model: {self._model_name} | "
            f"pair={t_pair_elapsed*1000:.1f}ms | "
            f"score={t_score_elapsed*1000:.1f}ms | "
            f"toplam={t_total_elapsed*1000:.1f}ms | "
            f"Top-1: {top1.get('law', '?')} m.{top1.get('article_no', '?')} "
            f"(cross_score={top1.get('cross_score', 0):.4f})"
        )

        return reranked + tail

    # ──────────────────────────────────────────────────────────────────────────
    # Yardımcı: Model Bilgisi
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        """Model hafızaya yüklenmiş mi?"""
        return self._model is not None

    @property
    def model_name(self) -> Optional[str]:
        """Aktif olarak yüklü model adı. Yüklü değilse None döner."""
        return self._model_name

    def __repr__(self) -> str:
        status = f"loaded={self._model_name}" if self._model else "not_loaded"
        return (
            f"CrossEncoderReranker("
            f"model={self.cfg.model!r}, "
            f"top_k={self.cfg.top_k}, "
            f"status={status!r})"
        )
