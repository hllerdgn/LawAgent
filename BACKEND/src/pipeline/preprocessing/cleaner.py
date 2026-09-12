"""
src/pipeline/preprocessing/cleaner.py — Ham JSON Temizleyici
=============================================================
Saf fonksiyon: ham dict alır, temiz dict döndürür.
Dosyaya yazmaz (storage.py yazar).
"""

import re
from datetime import datetime, timezone
from html import unescape


# ── Metin Temizleme Yardımcıları ──────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """HTML tag'lerini kaldırır, HTML entity'lerini çözer."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Fazla boşluk, tab ve yeni satırları tek boşluğa indirger."""
    text = re.sub(r"[ \t]+", " ", text)          # yatay boşluklar
    text = re.sub(r"\n{3,}", "\n\n", text)        # 3+ newline → 2 newline
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
    """Tek bir madde dict'ini temizler."""
    return {
        "no": _normalize_madde_no(article.get("no", "")),
        "baslik": _normalize_whitespace(_strip_html(article.get("baslik", ""))),
        "metin": _normalize_whitespace(_strip_html(article.get("metin", ""))),
    }


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────

def clean_raw(raw_data: dict) -> dict:
    """
    Scraper'dan gelen ham dict'i temizleyip normalize edilmiş dict döndürür.
    Dosyaya yazmaz.

    Args:
        raw_data: scrape_law() çıktısı

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
        if a.get("metin", "").strip()  # metni boş olan maddeleri atla
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
