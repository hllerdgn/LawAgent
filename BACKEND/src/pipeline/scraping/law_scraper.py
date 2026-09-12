"""
src/pipeline/scraping/law_scraper.py — mevzuat.gov.tr PDF Scraper
==================================================================
PDF tabanlı yaklaşım — HTML scraping yerine tercih edildi:
  • JS render riski yok (PDF statik)
  • Selector kırılganlığı yok
  • robots.txt'te Disallow yok — sadece Noindex (arama motoru direktifi)
  • PyMuPDF zaten requirements.txt'te mevcut

URL formatı: /MevzuatMetin/{tertip}.{tur}.{no}.pdf
  tertip=1 (Cumhuriyet), tur=5 (Kanun), no=<KanunNo>
  Örn: TMK/4721 → /MevzuatMetin/1.5.4721.pdf

Senkron fonksiyon — BackgroundTask içinde run_in_threadpool ile çağrılır.
Dosyaya yazmaz, sadece ham dict döndürür (storage.py yazar).

Retry: tenacity ile 5 deneme, exponential backoff (2s → 30s).
"""

import io
import re
from datetime import datetime, timezone
from typing import Optional

import fitz  # PyMuPDF
import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.logging import log

# ── Sabitler ──────────────────────────────────────────────────────────────────

_REQUEST_TIMEOUT = 60  # PDF büyük olabilir
_MEVZUAT_BASE = "https://www.mevzuat.gov.tr"
_PDF_PATH_TEMPLATE = "/MevzuatMetin/{tertip}.{tur}.{no}.pdf"

# Varsayılan: Cumhuriyet dönemi kanunları (tertip=1, tur=5)
_DEFAULT_TERTIP = "1"
_DEFAULT_TUR = "5"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LawAgentBot/1.0; academic-research)",
    "Accept": "application/pdf,*/*",
}

# Madde satırı kalıbı: "MADDE 1-", "Madde 23:", "MADDE 4 –" vb.
_ARTICLE_PATTERN = re.compile(
    r"^(MADDE|Madde)\s+(\d+)\s*[:\-–—]",
    re.MULTILINE,
)


# ── PDF İndirme ───────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    before_sleep=before_sleep_log(log, 20),  # logging.INFO
    reraise=True,
)
def _fetch_pdf_bytes(url: str) -> bytes:
    """PDF'yi indirir. RequestException → retry tetiklenir."""
    log.info(f"[Scraper] PDF indiriliyor: {url}")
    response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content


# ── PDF Parse ─────────────────────────────────────────────────────────────────

def _parse_pdf(pdf_bytes: bytes) -> tuple[str, list[dict]]:
    """
    PDF byte'larını parse ederek (law_name, articles) çifti döndürür.

    Madde ayrıştırma stratejisi:
    1. Her sayfanın metnini birleştir
    2. "MADDE N-" kalıbıyla metni böl
    3. Her parçayı madde olarak kaydet

    Returns:
        (law_name, articles)
        law_name: PDF metadata'dan veya ilk sayfadan çıkarılır
        articles: [{"no": str, "baslik": str, "metin": str}]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Kanun adı: önce metadata, sonra ilk sayfa ilk satır
    law_name = doc.metadata.get("title", "").strip()

    # Tüm sayfaları birleştir
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    if not law_name:
        # İlk anlamlı satırdan kanun adını çek
        for line in full_text.splitlines():
            line = line.strip()
            if len(line) > 10 and not line.startswith("MADDE"):
                law_name = line
                break

    # Maddeleri böl
    articles = []
    splits = _ARTICLE_PATTERN.split(full_text)
    # splits formatı: [ön_metin, "MADDE"/"Madde", "1", metin1, "MADDE"/"Madde", "2", metin2, ...]
    # İlk eleman madde öncesi içerik (kanun başlığı vb.), atla
    i = 1
    while i + 2 <= len(splits):
        madde_no = splits[i + 1].strip()
        metin_raw = splits[i + 2] if i + 2 < len(splits) else ""

        # Metin temizleme: ilk satır başlık olabilir
        lines = metin_raw.strip().splitlines()
        if lines and not re.match(r"^(MADDE|Madde)", lines[0]):
            baslik = lines[0].strip()
            metin = "\n".join(lines[1:]).strip()
        else:
            baslik = ""
            metin = metin_raw.strip()

        articles.append({
            "no": madde_no,
            "baslik": baslik,
            "metin": metin,
        })
        i += 3  # her madde: keyword + no + metin

    log.info(f"[Scraper] {len(articles)} madde parse edildi.")
    return law_name, articles


# ── URL Yardımcıları ──────────────────────────────────────────────────────────

def build_pdf_url(
    law_no: str,
    tertip: str = _DEFAULT_TERTIP,
    tur: str = _DEFAULT_TUR,
) -> str:
    """
    Kanun numarasından PDF URL'i oluşturur.
    Örn: build_pdf_url("4721") → "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.4721.pdf"
    """
    path = _PDF_PATH_TEMPLATE.format(tertip=tertip, tur=tur, no=law_no)
    return f"{_MEVZUAT_BASE}{path}"


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────

def scrape_law(
    law_id: str,
    url: str,
    law_name: Optional[str] = None,
) -> dict:
    """
    mevzuat.gov.tr'den kanun maddelerini PDF üzerinden çeker.

    Args:
        law_id:   Kanun kimliği (örn. "4721")
        url:      PDF URL'i — mevzuat.gov.tr/MevzuatMetin/... formatında olmalı
        law_name: Kanun adı (opsiyonel; PDF metadata'dan çıkarılmaya çalışılır)

    Returns:
        {
            "law_id": str,
            "law_name": str,
            "url": str,
            "scraped_at": str (ISO 8601),
            "articles": [{"no": str, "baslik": str, "metin": str}]
        }

    Raises:
        requests.RequestException: 5 retry sonrası bağlantı hatası
        fitz.FitzError: PDF bozuk veya parse edilemiyor
    """
    pdf_bytes = _fetch_pdf_bytes(url)
    parsed_name, articles = _parse_pdf(pdf_bytes)

    return {
        "law_id": law_id,
        "law_name": law_name or parsed_name or law_id,
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }
