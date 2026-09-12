"""
src/admin/schemas.py — Admin Scraping Pydantic Şemaları
========================================================
"""

import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from src.admin.job_store import JobStatus

# SSRF koruması: tam URL formatı regex ile doğrulanır
# Format: https://(www.)?mevzuat.gov.tr/MevzuatMetin/{Tur}.{Tertip}.{No}.pdf
# Path traversal (../../), sorgu string'i ve fragment yasak.
_MEVZUAT_PDF_RE = re.compile(
    r"^https://(www\.)?mevzuat\.gov\.tr/MevzuatMetin/\d+\.\d+\.\d+\.pdf$"
)


class ScrapeRequest(BaseModel):
    """Scraping tetikleme isteği."""
    law_id: str = Field(..., min_length=1, max_length=64, description="Kanun kimliği (örn. '6098')")
    law_name: str = Field(..., min_length=1, max_length=256, description="Kanun adı")
    url: str = Field(..., description="mevzuat.gov.tr URL'i")

    @field_validator("url")
    @classmethod
    def url_must_be_mevzuat_pdf(cls, v: str) -> str:
        """
        SSRF + path traversal koruması.
        Yalnızca tam eşleşen PDF URL'leri kabul edilir:
          https://(www.)?mevzuat.gov.tr/MevzuatMetin/{N}.{N}.{N}.pdf
        Sorgu dizisi, fragment veya ../ içeren URL'ler reddedilir.
        """
        if not _MEVZUAT_PDF_RE.match(v):
            raise ValueError(
                "URL geçerli bir mevzuat.gov.tr PDF adresi olmalıdır. "
                "Beklenen format: https://www.mevzuat.gov.tr/MevzuatMetin/{{Tur}}.{{Tertip}}.{{No}}.pdf"
            )
        return v


class ScrapeResponse(BaseModel):
    """Scraping başlatma yanıtı."""
    job_id: str
    status: JobStatus
    message: str


class PreprocessResponse(BaseModel):
    """Preprocessing tamamlama yanıtı."""
    job_id: str
    status: JobStatus
    clean_path: Optional[str] = None
    article_count: Optional[int] = None


class JobStatusResponse(BaseModel):
    """Tek job durum sorgusu yanıtı."""
    id: str
    law_id: str
    law_name: str
    status: JobStatus
    raw_path: Optional[str] = None
    clean_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    # Opsiyonel: raw veya clean veri (GET ?include_data=true ile)
    raw_data: Optional[dict[str, Any]] = None
    clean_data: Optional[dict[str, Any]] = None
