"""
src/admin/schemas.py — Admin Scraping Pydantic Şemaları
========================================================
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from src.admin.job_store import JobStatus

# mevzuat.gov.tr SSRF koruması için izin verilen domain'ler
_ALLOWED_URL_PREFIXES = (
    "https://www.mevzuat.gov.tr/",
    "https://mevzuat.gov.tr/",
)


class ScrapeRequest(BaseModel):
    """Scraping tetikleme isteği."""
    law_id: str = Field(..., min_length=1, max_length=64, description="Kanun kimliği (örn. '6098')")
    law_name: str = Field(..., min_length=1, max_length=256, description="Kanun adı")
    url: str = Field(..., description="mevzuat.gov.tr URL'i")

    @field_validator("url")
    @classmethod
    def url_must_be_mevzuat(cls, v: str) -> str:
        """SSRF koruması: yalnızca mevzuat.gov.tr domain'inden URL kabul edilir."""
        if not any(v.startswith(prefix) for prefix in _ALLOWED_URL_PREFIXES):
            raise ValueError(
                "URL yalnızca mevzuat.gov.tr domain'inden olabilir. "
                f"Geçerli prefix'ler: {_ALLOWED_URL_PREFIXES}"
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
