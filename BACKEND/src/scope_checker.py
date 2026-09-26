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

# Rota önbelleği (128 sorgu)
_route_cache: Dict[str, str] = {}


def is_legal_query(sorgu: str) -> bool:
    """Keyword tabanlı hızlı hukuk filtresi."""
    s = sorgu.lower()
    if any(hd in s.split() for hd in _HUKUK_DISI):
        return False
    if any(kd in s for kd in _KESIN_KAPSAM_DISI):
        return False
    return any(sig in s for sig in _HUKUKI_SINYALLER) or len(sorgu.split()) >= 3


def get_route(
    client: Any,
    sorgu: str,
    llm_completion_fn: Callable,
    company_doc_titles: list[str] = None,
) -> str:
    """
    Kullanıcı sorgusunun rotasını belirler:
    - 'company': Şirket/büro belgeleri ile ilgili
    - 'legal': TBK, TTK, TKHK veya hukuki danışmanlık/selamlama
    - 'out_of_scope': Tamamen hukuk/doküman dışı

    128 elemanlı LRU önbellek kullanılır.
    """
    company_doc_titles = company_doc_titles or []
    titles_key = "|".join(sorted(company_doc_titles))
    cache_key = f"{sorgu.lower().strip()}||{titles_key}"

    if cache_key in _route_cache:
        cached = _route_cache[cache_key]
        log.info(f"[Route / Cache] '{sorgu[:60]}' -> {cached}")
        return cached

    # Hızlı keyword filtreleri
    s = sorgu.lower().strip()
    # Kesin hukuk dışı konular
    if any(hd in s.split() for hd in _HUKUK_DISI):
        # Doküman adında geçmiyorsa reddet
        if not any(hd in t.lower() for t in company_doc_titles for hd in _HUKUK_DISI):
            log.info(f"[Route / Keyword] Hukuk dışı konu: '{sorgu[:60]}'")
            _route_cache[cache_key] = "out_of_scope"
            return "out_of_scope"

    doc_context = ""
    if company_doc_titles:
        doc_list_str = ", ".join(f"'{t}'" for t in company_doc_titles[:15])
        doc_context = (
            f"\nSistemde kayıtlı şirket/büro dokümanları mevcuttur: [{doc_list_str}].\n"
            "Kullanıcı bu dokümanlar, kurum içi kurallar, sözleşmeler veya şirket bilgileri "
            "hakkında soru soruyorsa 'company' kategorisini seç."
        )

    system_prompt = (
        "Sen bir akıllı sorgu yönlendiricisisin. "
        "Görevin kullanıcının sorusunu analiz ederek en uygun kategoriyi belirlemektir.\n\n"
        "Kategoriler:\n"
        "1. 'company': Kullanıcının sorusu şirket/büro/avukat dokümanları veya kurum içi konularla ilgiliyse.\n"
        "2. 'legal': Soru Türk Borçlar Kanunu (TBK), Ticaret Kanunu (TTK), Tüketici Kanunu (TKHK), "
        "dava, haklar, uyuşmazlıklar veya genel hukuki selamlama/sohbet ile ilgiliyse.\n"
        "3. 'out_of_scope': Soru hukuk veya şirket konularıyla tamamen ilgisiz genel bir konuysa "
        "(hava durumu, yemek, spor, film, oyun, dedikodu vb.).\n"
        f"{doc_context}\n"
        "YALNIZCA 'company', 'legal' veya 'out_of_scope' yaz. Başka hiçbir açıklama yapma."
    )

    try:
        yanit = llm_completion_fn(
            client=client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Soru: {sorgu}\n\nKategori (company / legal / out_of_scope):"},
            ],
            temperature=0.0,
            max_tokens=50,
        )
        karar = yanit.strip().lower()
        if "company" in karar and company_doc_titles:
            route = "company"
        elif "out_of_scope" in karar or "hayır" in karar:
            route = "out_of_scope"
        elif "legal" in karar or "evet" in karar:
            route = "legal"
        else:
            route = "legal" if is_legal_query(sorgu) else "out_of_scope"

        log.info(f"[Route / LLM] '{sorgu[:60]}' -> raw: '{karar[:20]}' -> karar: '{route}'")

        if len(_route_cache) >= 128:
            _route_cache.pop(next(iter(_route_cache)))
        _route_cache[cache_key] = route
        return route
    except Exception as e:
        log.warning(f"[Route / LLM] Hata, fallback devreye girdi: {e}")
        s = sorgu.lower().strip()
        if company_doc_titles and (
            any(t.lower() in s for t in company_doc_titles)
            or any(kw in s for kw in ["şirket", "büro", "avukat", "doküman", "belge", "kurum", "personel", "iç tüzük", "politika", "sözleşme", "adres"])
        ):
            return "company"
        route = "legal" if is_legal_query(sorgu) else "out_of_scope"
        return route


def clear_route_cache() -> None:
    """Rota önbelleğini sıfırlar (belge ekleme veya silme sonrası çağrılır)."""
    _route_cache.clear()


def is_in_scope_llm(client: Any, sorgu: str, llm_completion_fn: Callable) -> bool:
    """Geriye dönük uyumluluk: True = Kapsam içi, False = Kapsam dışı."""
    return get_route(client, sorgu, llm_completion_fn) != "out_of_scope"
