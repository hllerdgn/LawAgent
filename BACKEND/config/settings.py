"""
config/settings.py — LawAgent AI Merkezi Konfigürasyon
======================================================
Tüm ortam değişkenleri, ağırlıklar, eşikler ve model ayarları tek merkezde yönetilir.
"""

import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# .env dosyasını yükle
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_PATHS = [
    _BACKEND_DIR / ".env",
    _BACKEND_DIR.parent / ".env",
    Path("/content/drive/MyDrive/lawagent/.env"),
]
for _ep in _ENV_PATHS:
    if _ep.exists():
        load_dotenv(dotenv_path=_ep)
        break


@dataclass
class Settings:
    """Uygulama genel ayarları."""
    
    # ── Ortam ve Port ────────────────────────────────────────────────────────
    ENV: str = os.getenv("ENV", "production")
    PORT: int = int(os.getenv("PORT", "7860"))
    ALLOWED_ORIGINS: List[str] = field(
        default_factory=lambda: [
            o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
        ]
    )

    # ── LLM (Groq) Ayarları ──────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_FALLBACK_MODELS: List[str] = field(
        default_factory=lambda: [
            os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "llama-3.3-70b-versatile",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "groq/compound-mini",
        ]
    )
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2500"))

    # ── Qdrant Vektör Veritabanı ─────────────────────────────────────────────
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    QDRANT_STORAGE: Optional[str] = os.getenv("QDRANT_STORAGE")
    QDRANT_LOCAL_URL: str = os.getenv("QDRANT_LOCAL_URL", "http://localhost:6333")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "lawagent_mursit")
    SITE_COLLECTION_NAME: str = os.getenv("SITE_COLLECTION_NAME", "site_corpus")

    # ── Retrieval ve Ağırlık Ayarları ─────────────────────────────────────────
    TOP_K_DENSE: int = int(os.getenv("TOP_K_DENSE", "200"))
    TOP_K_BM25: int = int(os.getenv("TOP_K_BM25", "200"))
    FINAL_K: int = int(os.getenv("FINAL_K", "15"))
    DEFAULT_ASK_K: int = int(os.getenv("DEFAULT_ASK_K", "7"))
    MAX_SAME_ARTICLE: int = int(os.getenv("MAX_SAME_ARTICLE", "1"))
    
    # Hibrit Fusion Katsayıları
    ALPHA_DEFAULT: float = float(os.getenv("ALPHA_DEFAULT", "0.68"))
    ALPHA_EXACT: float = float(os.getenv("ALPHA_EXACT", "0.45"))
    ALPHA_SEMANTIC: float = float(os.getenv("ALPHA_SEMANTIC", "0.72"))
    ALPHA_SAME_LAW_BOOST: float = float(os.getenv("ALPHA_SAME_LAW_BOOST", "0.10"))
    SAME_LAW_DENSE_THRESHOLD: int = int(os.getenv("SAME_LAW_DENSE_THRESHOLD", "40"))
    DIVERSITY_PENALTY: float = float(os.getenv("DIVERSITY_PENALTY", "0.05"))

    # Boosting Katsayıları
    BOOST_MADDE: float = float(os.getenv("BOOST_MADDE", "35.0"))
    BOOST_ICTIHAT: float = float(os.getenv("BOOST_ICTIHAT", "6.0"))
    BOOST_KANUN: float = float(os.getenv("BOOST_KANUN", "6.0"))
    HYDE_WEIGHT: float = float(os.getenv("HYDE_WEIGHT", "0.80"))

    # Eşik Değerleri
    MIN_RELEVANCE_SCORE: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.15"))
    MIN_FALLBACK_SCORE: float = float(os.getenv("MIN_FALLBACK_SCORE", "0.25"))

    # ── Cross-Encoder Reranker ───────────────────────────────────────────────
    ENABLE_CROSS_RERANK: bool = os.getenv("ENABLE_CROSS_RERANK", "true").lower() == "true"
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    RERANKER_FALLBACK: str = os.getenv("RERANKER_FALLBACK", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    RERANKER_TOP_K: int = int(os.getenv("RERANKER_TOP_K", "30"))
    RERANKER_DEVICE: str = os.getenv("RERANKER_DEVICE", "cpu")

    # ── Dosya Yolları ─────────────────────────────────────────────────────────
    BASE_DIR: Path = _BACKEND_DIR
    DATA_DIR: Path = _BACKEND_DIR / "src" / "data"
    CACHE_PATH: Path = _BACKEND_DIR / "src" / "data" / "retriever_cache.pkl"
    ENRICHED_PATH: Path = _BACKEND_DIR / "src" / "data" / "chunk_corpus_enriched.json"
    CLIENTS_FILE: Path = _BACKEND_DIR / "src" / "clients.json"
    SITE_DOCS_FILE: Path = _BACKEND_DIR / "data" / "site_documents.json"


# Singleton Settings nesnesi
settings = Settings()
