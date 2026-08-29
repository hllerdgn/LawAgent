"""
src/scope_checker.py — LawAgent AI Hukuki Kapsam Denetimi
=========================================================
Kullanıcı sorgularının TBK, TTK, TKHK kapsamında olup olmadığını
keyword eşleştirme ve LLM sınıflandırmasıyla denetler.
"""

import re
import logging
from typing import Dict, Any, Callable

log = logging.getLogger("LawAgent.ScopeChecker")

_HUKUK_DISI = {
    "hava", "yemek", "müzik", "film", "spor", "oyun", "minecraft",
    "magazin", "haber", "gündem", "sağlık", "doktor", "ilaç",
    "matematik", "fizik", "kimya",
}

# Kesin kapsam dışı konular — bu kelimeler sorguda geçerse direkt reddedilir
_KESIN_KAPSAM_DISI = [
    # Vergi hukuku
    "vergi", "kdv", "gelir vergisi", "kurumlar vergisi", "mtv", "ötv", "stopaj",
    # Ceza hukuku
    "suç", "ceza", "hapis", "tutuklama", "gözaltı", "savcı", "müdahil", "beraat",
    "uyuşturucu", "kaçakçılık", "dolandırıcılık", "sahte", "hırsız",
    # Aile hukuku
    "boşan", "boşama", "boşamak", "nafaka", "velayet", "evlilik",
    # İdare hukuku
    "belediye", "ruhsat", "ihale", "kamu ihale",
    # Diğer kapsam dışı
    "pasaport", "vize", "vatandaşlık", "askerlik",
]

_HUKUKI_SINYALLER = {
    "nedir", "nasıl", "hak", "kanun", "madde", "dava", "sözleşme",
    "tazminat", "kira", "borç", "alacak", "fesih", "temerrüt",
    "cayma", "garanti", "tahliye", "tbk", "tkhk", "ttk",
    "6098", "6502", "6102", "mahkeme", "icra", "ipotek",
    "miras", "velayet",
}

KAPSAM_DISI_YANITI = (
    "Üzgünüm, bu konu uzmanlık alanım olan TBK (Türk Borçlar Kanunu), "
    "TTK (Türk Ticaret Kanunu) ve TKHK (Tüketicinin Korunması Hakkında Kanun) "
    "dışında kalmaktadır. Bu alanlarda yardımcı olmaktan memnuniyet duyarım."
)

_KAPSAM_KONTROL_SISTEM = (
    "Sen bir Türk hukuku kapsam denetçisisin. "
    "Görevin: kullanıcının sorusunun yalnızca şu üç kanun kapsamında olup olmadığını belirlemek: "
    "Türk Borçlar Kanunu (TBK), Türk Ticaret Kanunu (TTK), Tüketicinin Korunması Hakkında Kanun (TKHK). "
    "Selamlama ve genel sohbet mesajları da KAPSAM İÇİ say. "
    "Yalnızca 'EVET' veya 'HAYIR' olarak yanıt ver. Başka hiçbir şey yazma."
)

# Aynı sorgu için tekrar LLM çağrısı yapılmasın (128 sorgu önbelleği)
_scope_cache: Dict[str, bool] = {}


def is_legal_query(sorgu: str) -> bool:
    """Keyword tabanlı hızlı hukuk filtresi."""
    s = sorgu.lower()
    if any(hd in s.split() for hd in _HUKUK_DISI):
        return False
    if any(kd in s for kd in _KESIN_KAPSAM_DISI):
        return False
    return any(sig in s for sig in _HUKUKI_SINYALLER) or len(sorgu.split()) >= 3


def is_in_scope_llm(client: Any, sorgu: str, llm_completion_fn: Callable) -> bool:
    """LLM ile kapsam kontrolü.
    True  = TBK/TTK/TKHK kapsamında → işleme devam et
    False = Kapsam dışı → reddet
    Hata durumunda keyword tabanlı is_legal_query() fallback olarak kullanılır.
    """
    cache_key = sorgu.lower().strip()

    # Önbellek kontrolü — aynı sorgu için LLM'e gitme
    if cache_key in _scope_cache:
        log.info(f"[Kapsam Kontrol / Cache] '{sorgu[:60]}' → {'İçi' if _scope_cache[cache_key] else 'Dışı'}")
        return _scope_cache[cache_key]

    # Önce açıkça kapsam dışı kelimelere hızlı bak (maliyet sıfır)
    s = cache_key
    if any(kd in s for kd in _KESIN_KAPSAM_DISI):
        log.info(f"[Kapsam Kontrol / Keyword] Kapsam dışı: '{sorgu[:60]}'")
        _scope_cache[cache_key] = False
        return False
    if any(hd in s.split() for hd in _HUKUK_DISI):
        log.info(f"[Kapsam Kontrol / Keyword] Hukuk dışı konu: '{sorgu[:60]}'")
        _scope_cache[cache_key] = False
        return False

    # LLM ile derin kapsam analizi
    try:
        yanit = llm_completion_fn(
            client=client,
            messages=[
                {"role": "system", "content": _KAPSAM_KONTROL_SISTEM},
                {
                    "role": "user",
                    "content": f"Soru: {sorgu}\n\nBu soru TBK, TTK veya TKHK kapsamında mı? (EVET/HAYIR)",
                },
            ],
            temperature=0.0,
            max_tokens=400,
        )
        karar = yanit.strip().upper()
        if re.search(r"\bEVET\b", karar):
            kapsam_ici = True
        elif re.search(r"\bHAYIR\b", karar):
            kapsam_ici = False
        else:
            log.warning(f"[Kapsam Kontrol / LLM] Belirsiz yanıt '{karar[:30]}', kapsam içi varsayıldı")
            kapsam_ici = True
        log.info(f"[Kapsam Kontrol / LLM] '{sorgu[:60]}' → {karar[:20]} → {'İçi' if kapsam_ici else 'Dışı'}")
        if len(_scope_cache) >= 128:
            _scope_cache.pop(next(iter(_scope_cache)))
        _scope_cache[cache_key] = kapsam_ici
        return kapsam_ici
    except Exception as e:
        log.warning(f"[Kapsam Kontrol / LLM] Hata, keyword fallback devreye girdi: {e}")
        return is_legal_query(sorgu)
