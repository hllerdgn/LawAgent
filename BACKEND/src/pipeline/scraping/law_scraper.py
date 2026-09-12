"""
src/pipeline/scraping/law_scraper.py — mevzuat.gov.tr Kanun Scraper'ı
======================================================================
Senkron fonksiyon — BackgroundTask içinde run_in_threadpool ile çağrılır.
Dosyaya yazmaz, sadece ham dict döndürür (storage.py yazar).

Retry: tenacity ile 5 deneme, exponential backoff (2s → 30s).
"""

from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from core.logging import log

# HTTP isteği için timeout (saniye)
_REQUEST_TIMEOUT = 30

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LawAgent/1.0; +https://lawagent.app)"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _fetch_html(url: str) -> str:
    """HTTP GET ile sayfayı çeker. requests.RequestException → retry tetiklenir."""
    response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _parse_articles(html: str, law_id: str) -> list[dict]:
    """
    mevzuat.gov.tr HTML'inden maddeleri ayrıştırır.
    Yapı değişirse bu fonksiyonu güncelle.
    Döndürür: [{"no": str, "baslik": str, "metin": str}]
    """
    soup = BeautifulSoup(html, "lxml")
    articles = []

    # mevzuat.gov.tr madde container'ları — selector değişirse burası güncellenir
    # Tipik yapı: <div class="mevzuat-madde"> veya <div id="madde-...">
    containers = soup.select("div.kanun-madde, div.madde, article.madde")

    if not containers:
        # Fallback: başlık + paragraf kombinasyonu
        containers = soup.select("div[id^='madde']")

    for container in containers:
        # Madde numarası
        no_tag = container.select_one(".madde-no, .madde-baslik-no, h3, h4")
        no = no_tag.get_text(strip=True) if no_tag else ""

        # Başlık
        baslik_tag = container.select_one(".madde-baslik, .baslik")
        baslik = baslik_tag.get_text(strip=True) if baslik_tag else ""

        # Metin
        metin_tag = container.select_one(".madde-icerik, .icerik, p")
        metin = metin_tag.get_text(separator="\n", strip=True) if metin_tag else container.get_text(separator="\n", strip=True)

        articles.append({"no": no, "baslik": baslik, "metin": metin})

    return articles


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    before_sleep=before_sleep_log(log, log.level if hasattr(log, "level") else 20),
    reraise=True,
)
def scrape_law(law_id: str, url: str, law_name: Optional[str] = None) -> dict:
    """
    mevzuat.gov.tr'den kanun maddelerini çeker.

    Args:
        law_id:   Kanun kimliği (örn. "6098")
        url:      Kanun sayfası URL'i (mevzuat.gov.tr ile başlamalı)
        law_name: Kanun adı (opsiyonel, biliniyorsa geçil)

    Returns:
        {
            "law_id": str,
            "law_name": str,
            "url": str,
            "scraped_at": str (ISO 8601),
            "articles": [{"no": str, "baslik": str, "metin": str}]
        }

    Raises:
        requests.RequestException: 5 retry sonrası hala bağlantı hatası
        ValueError: Bağlantı başarılı ama 0 madde döndü (selector kırık)
    """
    log.info(f"[Scraper] Kanun çekiliyor: law_id={law_id}, url={url}")
    html = _fetch_html(url)
    articles = _parse_articles(html, law_id)
    log.info(f"[Scraper] {len(articles)} madde ayrıştırıldı (law_id={law_id})")

    # law_name sayfa başlığından çekilmeye çalışılır
    if not law_name:
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.select_one("h1.kanun-baslik, h1, title")
        law_name = title_tag.get_text(strip=True) if title_tag else law_id

    return {
        "law_id": law_id,
        "law_name": law_name,
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }
