"""
config/settings.py — LawAgent AI Merkezi Konfigürasyon
======================================================
Tüm ortam değişkenleri, ağırlıklar, eşikler ve model ayarları
tek merkezde Pydantic BaseSettings ile yönetilir.

Faydaları:
  - Tip doğrulama + startup'ta fail-fast (zorunlu değişken eksikse)
  - .env otomatik yükleme
  - IDE otomatik tamamlama
"""

import warnings
from pathlib import Path
from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Uygulama genel ayarları — .env ve ortam değişkenlerinden otomatik yüklenir."""

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",       # Tanımsız env var'ları sessizce yoksay
        case_sensitive=True,
    )

    # ── Ortam ve Port ────────────────────────────────────────────────────────
    ENV: str = "production"
    PORT: int = 7860
    ALLOWED_ORIGINS: List[str] = ["*"]

    # ── LLM (Groq) Ayarları ──────────────────────────────────────────────────
    GROQ_API_KEY: str = ""              # Boşsa uygulama LLM çağrısı yapamaz
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2500

    # ── Qdrant Vektör Veritabanı ─────────────────────────────────────────────
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_STORAGE: Optional[str] = None
    QDRANT_LOCAL_URL: str = "http://localhost:6333"
    COLLECTION_NAME: str = "lawagent_mursit"
    SITE_COLLECTION_NAME: str = "site_corpus"

    # ── Retrieval ve Ağırlık Ayarları ─────────────────────────────────────────
    TOP_K_DENSE: int = 200
    TOP_K_BM25: int = 200
    FINAL_K: int = 15
    DEFAULT_ASK_K: int = 7
    MAX_SAME_ARTICLE: int = 1

    # Hibrit Fusion Katsayıları
    ALPHA_DEFAULT: float = 0.68
    ALPHA_EXACT: float = 0.45
    ALPHA_SEMANTIC: float = 0.72
    ALPHA_SAME_LAW_BOOST: float = 0.10
    SAME_LAW_DENSE_THRESHOLD: int = 40
    DIVERSITY_PENALTY: float = 0.05

    # Boosting Katsayıları
    BOOST_MADDE: float = 35.0
    BOOST_ICTIHAT: float = 6.0
    BOOST_KANUN: float = 6.0
    HYDE_WEIGHT: float = 0.80

    # Eşik Değerleri
    MIN_RELEVANCE_SCORE: float = 0.15
    MIN_FALLBACK_SCORE: float = 0.25

    # ── Cross-Encoder Reranker ───────────────────────────────────────────────
    ENABLE_CROSS_RERANK: bool = True
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANKER_FALLBACK: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 30
    RERANKER_MAX_DOC_CHARS: int = 512
    RERANKER_DEVICE: str = "cpu"

    # ── Dinamik Sorgu Genişletme (Step-Back & Concept Expansion) ──────────────
    ENABLE_DYNAMIC_EXPANSION: bool = True
    EXPANSION_MODEL: str = "groq/compound-mini"

    # ── Güvenlik ──────────────────────────────────────────────────────────────
    ADMIN_API_KEY: Optional[str] = None   # Admin endpoint'leri için — boşsa uyarı

    # ── Monitoring ────────────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None      # Sentry error tracking DSN

    # ── Validators ───────────────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        """Production ortamında gevşek konfigürasyonlar için uyarı üretir."""
        if self.ENV == "production":
            if self.ALLOWED_ORIGINS == ["*"]:
                warnings.warn(
                    "[Security] ALLOWED_ORIGINS='*' — production'da "
                    "ALLOWED_ORIGINS env var'ını whitelist ile ayarlamanız önerilir.",
                    UserWarning,
                    stacklevel=2,
                )
            if not self.ADMIN_API_KEY:
                warnings.warn(
                    "[Security] ADMIN_API_KEY ayarlanmamış — admin endpoint'leri "
                    "korumasız çalışacak.",
                    UserWarning,
                    stacklevel=2,
                )
            if not self.GROQ_API_KEY:
                warnings.warn(
                    "[Config] GROQ_API_KEY ayarlanmamış — LLM çağrıları başarısız olacak.",
                    UserWarning,
                    stacklevel=2,
                )
        return self

    # ── Hesaplanmış Dosya Yolları (env'den değil, _BACKEND_DIR'dan) ──────────

    @property
    def BASE_DIR(self) -> Path:
        return _BACKEND_DIR

    @property
    def DATA_DIR(self) -> Path:
        return _BACKEND_DIR / "src" / "data"

    @property
    def CACHE_PATH(self) -> Path:
        return _BACKEND_DIR / "src" / "data" / "retriever_cache.pkl"

    @property
    def ENRICHED_PATH(self) -> Path:
        return _BACKEND_DIR / "src" / "data" / "chunk_corpus_enriched.json"

    @property
    def CLIENTS_FILE(self) -> Path:
        return _BACKEND_DIR / "src" / "clients.json"

    @property
    def SITE_DOCS_FILE(self) -> Path:
        return _BACKEND_DIR / "data" / "site_documents.json"

    @property
    def GROQ_FALLBACK_MODELS(self) -> List[str]:
        """Öncelikli Groq modeli başta olmak üzere sıralı fallback listesi."""
        seen: set = set()
        models: List[str] = []
        candidates = [
            self.GROQ_MODEL,
            "llama-3.3-70b-versatile",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "groq/compound-mini",
        ]
        for m in candidates:
            if m and m not in seen:
                seen.add(m)
                models.append(m)
        return models


# Singleton Settings nesnesi
settings = Settings()
