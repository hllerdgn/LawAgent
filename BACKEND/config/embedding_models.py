"""
config/embedding_models.py  —  LawAgent Model Registry
=======================================================

Bu dosya, embedding modeli yapılandırmalarını merkezi olarak tanımlar.

KRİTİK İZOLASYON KURALI:
  - Production kodu (retriever.py, generator.py) YALNIZCA active=True olan girişi kullanır.
  - shadow_* girişleri HİÇBİR ZAMAN production serving path'ine dahil edilmez.
  - Bu dosyaya yeni shadow model eklemek ya da çıkarmak production'ı ETKİLEMEZ.
  - "active" alanı değiştirilmeden önce get_active_model() ile mevcut durum doğrulanmalıdır.

PROMOSYON PROSEDÜRÜ (manuel, asla otomatik değil):
  1. Shadow modelin eval sonuçları prod'u net geçti mi?
     (Bootstrap CI örtüşmüyor, TKHK dahil tüm kategoriler dengeli, latency kabul edilebilir?)
  2. Evet ise:
       a. shadow_x: active=False → active=True
       b. production: active=True → active=False
  3. Aynı anda sadece BİR kayıt active=True olabilir — get_active_model() bunu zorunlu kılar.
  4. Değişiklikten sonra FastAPI servisini yeniden başlat (embedder yeniden yüklenir).
"""

from __future__ import annotations
import os

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BACKEND_DIR, "src", "data")

# ─────────────────────────────────────────────────────────────────────────────
# MODEL REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

EMBEDDING_MODEL_REGISTRY: dict[str, dict] = {

    # ── PRODUCTION ────────────────────────────────────────────────────────────
    "production": {
        "model_id": "newmindai/Mursit-Base-TR-Retrieval",
        "hf_repo": "newmindai/Mursit-Base-TR-Retrieval",
        "local_path": os.path.join(_DATA_DIR, "fine_tuned_mursit"),
        "collection": "lawagent_mursit",         # PRODUCTION — ASLA YENİDEN YAZMA
        "vector_dim": 768,
        "active": True,                          # Bu flag'i değiştirmeden önce PROMOSYON PROSEDÜRÜ'nü oku
        "query_prefix": "query: ",
        "doc_prefix": "",
        "quantize": True,                        # int8 quantize (mursit_int8.pt)
        "notes": "Fine-tuned v1_full (contrastive, early-stop epoch 2), int8 quantized. "
                 "Held-Out Hit@1=0.733, MRR=0.800. PROD model.",
    },

    # ── SHADOW: Mursit-Large-TR-Retrieval ────────────────────────────────────
    "shadow_mursit_large": {
        "model_id": "newmindai/Mursit-Large-TR-Retrieval",
        "hf_repo": "newmindai/Mursit-Large-TR-Retrieval",
        "local_path": None,                      # İlk çalıştırmada HF'den otomatik indirilir
        "collection": "legal_chunks_mursit_large_shadow",
        "vector_dim": 1024,                      # ModernBERT-large embedding dim
        "active": False,                         # ASLA True yapma — sadece eval'de kullan
        "query_prefix": "query: ",
        "doc_prefix": "",
        "quantize": False,
        "notes": "403M ModernBERT-large, aynı aile, MTEB=56.87, Legal Score=46.56. "
                 "Shadow eval: production collection'a dokunmaz.",
    },

    # ── SHADOW: TurkEmbed4Retrieval (Mecellem yerine) ─────────────────────────
    "shadow_turk4retrieval": {
        "model_id": "newmindai/TurkEmbed4Retrieval",
        "hf_repo": "newmindai/TurkEmbed4Retrieval",
        "local_path": None,
        "collection": "legal_chunks_turk4retrieval_shadow",
        "vector_dim": 768,
        "active": False,
        "query_prefix": "",
        "doc_prefix": "",
        "quantize": False,
        "notes": "newmindai/TurkEmbed4Retrieval — sentence-transformers uyumlu, Türkçe retrieval. "
                 "Mecellem Encoder newmindai'de kamuya açık olmadığından tercih edildi (2025-07-30).",
    },

    # ── SHADOW: BGE-M3 (opsiyonel, düşük öncelik) ────────────────────────────
    "shadow_bge_m3": {
        "model_id": "BAAI/bge-m3",
        "hf_repo": "BAAI/bge-m3",
        "local_path": None,
        "collection": "legal_chunks_bge_m3_shadow",
        "vector_dim": 1024,
        "active": False,
        "query_prefix": "",
        "doc_prefix": "",
        "quantize": False,
        "notes": "568M çok dilli genel-amaçlı referans model. Opsiyonel, düşük öncelik.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────────────────────

def get_active_model() -> tuple[str, dict]:
    """
    Registry'den active=True olan tek modeli döndürür.
    Birden fazla ya da sıfır aktif model varsa ValueError fırlatır.
    Production kodu bu fonksiyonu kullanır — shadow modellere asla dokunmaz.
    """
    active = [(k, v) for k, v in EMBEDDING_MODEL_REGISTRY.items() if v.get("active")]
    if len(active) == 0:
        raise ValueError("Model registry'de active=True olan model bulunamadı!")
    if len(active) > 1:
        raise ValueError(
            f"Registry'de birden fazla aktif model var: {[k for k, _ in active]}. "
            "Aynı anda yalnızca bir model active=True olabilir."
        )
    return active[0]


def get_model_config(model_key: str) -> dict:
    """
    Verilen model_key için registry yapılandırmasını döndürür.
    Bilinmeyen key varsa KeyError fırlatır.
    """
    if model_key not in EMBEDDING_MODEL_REGISTRY:
        available = list(EMBEDDING_MODEL_REGISTRY.keys())
        raise KeyError(
            f"'{model_key}' registry'de bulunamadı. "
            f"Mevcut model anahtarları: {available}"
        )
    return EMBEDDING_MODEL_REGISTRY[model_key]


def list_shadow_models() -> list[str]:
    """Shadow (active=False) model anahtarlarını listeler."""
    return [k for k, v in EMBEDDING_MODEL_REGISTRY.items() if not v.get("active")]


def is_production_collection(collection_name: str) -> bool:
    """
    Verilen collection adının production collection'ı olup olmadığını kontrol eder.
    Shadow encode/cleanup kodunda güvenlik katmanı olarak kullanılır.
    """
    _, prod_cfg = get_active_model()
    return collection_name == prod_cfg["collection"]
