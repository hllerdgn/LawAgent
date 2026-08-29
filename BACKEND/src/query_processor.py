"""
src/query_processor.py — LawAgent AI Sorgu İşleme ve Niyet Yönlendirici
======================================================================
Sorgu yeniden yazma (query rewrite), niyet tespiti (intent router)
ve içtihat talebi algılama işlemlerini yürütür.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Callable

log = logging.getLogger("LawAgent.QueryProcessor")

# ── İçtihat Talebi Kontrolü ───────────────────────────────────────────────────

_ICTIHAT_ISTEGI_KELIMELERI = {
    "evet", "isterim", "istiyorum", "göster", "gösterin", "bakalım",
    "emsal", "karar", "içtihat", "yargıtay", "lütfen", "tabii", "tabi",
    "olur", "harika", "güzel",
}
_ICTIHAT_SORUSU_TETIKLEYICI = "emsal karar"


def is_ictihat_request(sorgu: str, history: List[Dict]) -> bool:
    """Kullanıcının önceki cevaptaki içtihat önerisine olumlu yanıt verip vermediğini denetler."""
    if not history:
        return False
    last_msg = history[-1]
    if last_msg.get("role") != "assistant":
        return False
    if _ICTIHAT_SORUSU_TETIKLEYICI not in last_msg.get("content", "").lower():
        return False
    sorgu_temiz = sorgu.lower().strip()
    return any(kelime in sorgu_temiz for kelime in _ICTIHAT_ISTEGI_KELIMELERI)


# ── Query Intent Router ───────────────────────────────────────────────────────

class QueryIntentRouter:
    INTENT_DEFINITIONS = {
        "INFO_RETRIEVAL": {
            "keywords": ["nedir", "ne", "neyin", "nasıl", "hangi", "kaç"],
            "retrieval_k": 7,
        },
        "COMPARISON": {
            "keywords": ["fark", "arasında", "farklı", "ne kadar", "vs", "karşılaştır"],
            "retrieval_k": 10,
        },
        "PROCEDURE": {
            "keywords": ["süre", "yapılır", "adım", "işlem", "başvuru", "başvur"],
            "retrieval_k": 8,
        },
        "RIGHTS_OBLIGATION": {
            "keywords": ["hak", "sorumluluk", "yükümlülük", "ödeme", "iade"],
            "retrieval_k": 7,
        },
        "CONSEQUENCE": {
            "keywords": ["sonuç", "ceza", "para", "tazminat", "zarar", "risiko"],
            "retrieval_k": 6,
        },
    }

    def __init__(self, client: Any = None):
        self.client = client

    def detect_intent(self, sorgu: str) -> Tuple[str, int]:
        sorgu_lower = sorgu.lower()
        best_intent = "INFO_RETRIEVAL"
        best_score = 0
        for intent, config in self.INTENT_DEFINITIONS.items():
            score = sum(1 for kw in config["keywords"] if kw in sorgu_lower)
            if score > best_score:
                best_score = score
                best_intent = intent
        recommended_k = self.INTENT_DEFINITIONS[best_intent]["retrieval_k"]
        log.info(f"Intent Detection: {best_intent} (k={recommended_k})")
        return best_intent, recommended_k


# ── Query Rewrite ─────────────────────────────────────────────────────────────

_MADDE_REF_RE = re.compile(
    r"\b(tbk|tkhk|ttk)\s*(?:m\.|madde)?\s*\d+\b|\b(6098|6502|6102)\b|\b(?:madde|m\.)\s*\d+\b",
    re.IGNORECASE,
)
_REWRITE_SYSTEM = (
    "Sen Türk hukuku uzmanısın. Kullanıcının sorusunu, anlamını bozmadan "
    "akademik hukuk terimleriyle yeniden yaz. Kanun kısaltmalarını (TBK, TKHK, TTK) koru. "
    "Sadece yeniden yazılmış soruyu döndür, açıklama ekleme."
)


def has_madde_ref(sorgu: str) -> bool:
    return bool(_MADDE_REF_RE.search(sorgu))


def rewrite_query(client: Any, sorgu: str, llm_completion_fn: Callable) -> str:
    """Sorguda doğrudan madde referansı yoksa akademik hukuk terimlerine dönüştürür."""
    if has_madde_ref(sorgu):
        return sorgu
    if len(sorgu.split()) < 4 or len(sorgu.split()) > 30:
        return sorgu
    try:
        yeni = llm_completion_fn(
            client=client,
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": f"Soru: {sorgu}\n\nYeniden yazılmış hali:"},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        return yeni if yeni and len(yeni) <= 300 else sorgu
    except Exception as e:
        log.warning(f"Query rewrite hatası: {e}")
        return sorgu
