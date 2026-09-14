"""
src/pipeline/preprocessing/cleaner.py — Ham JSON Temizleyici
=============================================================
Saf fonksiyon: ham dict alır, temiz dict döndürür.
Dosyaya yazmaz (storage.py yazar).

Sorumluluk sınırı:
  - law_scraper.py  → ham metin çıkarmak + kaba madde ayrımı (dipnotlar dahil)
  - cleaner.py      → dipnot ayıklama + whitespace normalize + madde no standart
Bu ayrım sayesinde temizleme mantığı değişirse sadece preprocess endpoint'i
tekrar çağırmak yeterli — yeniden scrape gerekmez.
"""

import re
from datetime import datetime, timezone
from html import unescape


# ── Dipnot Kalıpları ─────────────────────────────────────────────────────────
# Mevzuat PDF'lerinde madde metnine gömülü gelen referans/değişiklik notları.
# Ham raw'da görünür halde kalır; preprocess adımında ayıklanır.
#
# Örn: "(Değişik: 10/9/2014-6552/76 md.)"
# Örn: "(Ek: 1/3/2018-7099/25 md.)"
# Örn: "(Mülga: 6/2/2014-6518/106 md.)"
# Örn: "6 2/7/2018 tarihli ve 700 sayılı KHK'nin 156 ncı maddesiyle..."
_DIPNOT_PATTERNS = [
    # Parantez içi değişiklik notları: (Değişik: ...), (Ek: ...), (Mülga: ...)
    re.compile(r"\((?:Değişik|Ek|Mülga|Bent|Fıkra|Kaldırılan)[^)]{0,300}\)"),
    # Numeral + tarih formatı: "6 2/7/2018 tarihli ve..."
    re.compile(r"^\d{1,2}\s+\d{1,2}/\d{1,2}/\d{4}[^\n]{0,300}", re.MULTILINE),
    # Resmi Gazete referansları: "3 30/6/2012-6362/146 md." vb.
    re.compile(r"^\d{1,2}\s+(?:\d+/\d+-\d+|RG)[^\n]{0,300}", re.MULTILINE),
    # KHK şerhleri: "sayılı KHK'nin ... maddesiyle..."
    re.compile(r"\d+\s+say\u0131l\u0131\s+KHK[^\n]{0,200}", re.MULTILINE),
]


# ── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def _clean_footnotes(text: str) -> str:
    """
    Madde metnine gömülü dipnot ve değişiklik notlarını ayıklar.
    Ham raw metni olduğu gibi bırakır — bu fonksiyon sadece cleaner.py'de.
    """
    for pattern in _DIPNOT_PATTERNS:
        text = pattern.sub("", text)
    # Temizlik sonrası oluşan birden fazla boş satırı topla
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_html(text: str) -> str:
    """HTML tag'lerini kaldırır, HTML entity'lerini çözer."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Fazla boşluk, tab ve yeni satırları normalize eder."""
    text = re.sub(r"[ \t]+", " ", text)    # yatay boşluklar → tek boşluk
    text = re.sub(r"\n{3,}", "\n\n", text) # 3+ newline → 2 newline
    return text.strip()


def _normalize_madde_no(no: str) -> str:
    """
    Madde numarasını standart formata getirir.
    Örn: "MADDE 4-" → "4", "Md. 12:" → "12", "  MADDE 7  " → "7"
    """
    no = no.strip()
    no = re.sub(r"(?i)^(madde|md\.?)\s*", "", no)
    no = re.sub(r"[:\-–—]+$", "", no)
    return no.strip()


def _clean_article(article: dict) -> dict:
    """Tek bir madde dict'ini tam temizlik pipeline'ından geçirir."""
    metin_raw = article.get("metin", "")
    # Sıra önemli: önce HTML, sonra dipnot, sonra whitespace normalize
    metin = _normalize_whitespace(_clean_footnotes(_strip_html(metin_raw)))
    baslik = _normalize_whitespace(_strip_html(article.get("baslik", "")))
    return {
        "no": _normalize_madde_no(article.get("no", "")),
        "baslik": baslik,
        "metin": metin,
    }


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────

def clean_raw(raw_data: dict) -> dict:
    """
    Scraper'dan gelen ham dict'i temizleyip normalize edilmiş dict döndürür.
    Dosyaya yazmaz (storage.py yazar).

    Pipeline:
      1. HTML entity/tag temizle
      2. Dipnot ve değişiklik notlarını ayıkla  ← _clean_footnotes burada
      3. Whitespace normalize
      4. Madde numarasını standartlaştır
      5. Boş maddeleri filtrele

    Args:
        raw_data: scrape_law() çıktısı — dipnotlar ham halde

    Returns:
        {
            "law_id": str,
            "law_name": str,
            "source_url": str,
            "scraped_at": str,
            "cleaned_at": str (ISO 8601),
            "article_count": int,
            "articles": [{"no": str, "baslik": str, "metin": str}]
        }

    Raises:
        ValueError: raw_data boş veya articles alanı eksik
    """
    if not raw_data or "articles" not in raw_data:
        raise ValueError("Geçersiz ham veri: 'articles' alanı bulunamadı.")

    cleaned_articles = [
        _clean_article(a)
        for a in raw_data["articles"]
        if a.get("metin", "").strip()  # tamamen boş maddeleri atla
    ]

    return {
        "law_id": raw_data.get("law_id", ""),
        "law_name": _normalize_whitespace(raw_data.get("law_name", "")),
        "source_url": raw_data.get("url", ""),
        "scraped_at": raw_data.get("scraped_at", ""),
        "cleaned_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(cleaned_articles),
        "articles": cleaned_articles,
    }
