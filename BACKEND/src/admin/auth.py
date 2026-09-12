"""
src/admin/auth.py — Admin Kimlik Doğrulama
==========================================
X-Admin-Key header kontrolü.
Startup'ta production ortamında key yoksa uygulamayı başlatmaz.
"""

from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from config.settings import settings
from core.logging import log

_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def check_admin_key_at_startup() -> None:
    """
    Uygulama lifespan başlangıcında çağrılır.
    ENV=production iken ADMIN_API_KEY boşsa uygulamayı başlatmaz.
    """
    if settings.ENV == "production" and not settings.ADMIN_API_KEY:
        raise RuntimeError(
            "[Auth] ADMIN_API_KEY env var zorunludur (ENV=production). "
            "Uygulamayı başlatmak için bu değeri .env dosyasına veya "
            "ortam değişkenlerine ekleyin."
        )
    if not settings.ADMIN_API_KEY:
        log.warning(
            "[Auth] ADMIN_API_KEY ayarlanmamış — admin endpoint'leri "
            "korumasız çalışıyor (dev modu). Production'da bu kabul edilemez."
        )


async def verify_admin_key(key: Optional[str] = Security(_admin_key_header)) -> None:
    """
    FastAPI Depends() ile kullanılır.
    ADMIN_API_KEY ayarlıysa header'ı doğrular, yanlışsa 403.
    ADMIN_API_KEY boşsa (dev modu) geçişe izin verir.
    """
    if not settings.ADMIN_API_KEY:
        return
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı.")
