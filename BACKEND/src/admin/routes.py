"""
src/admin/routes.py — Admin Scraping Router
============================================
Endpoint'ler:
  POST /admin/scrape                      → scraping başlat
  GET  /admin/scrape                      → tüm jobları listele
  GET  /admin/scrape/{job_id}             → job durumu + opsiyonel veri
  POST /admin/scrape/{job_id}/preprocess  → preprocessing çalıştır
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from core.logging import log
from src.admin import job_store
from src.admin.auth import verify_admin_key
from src.admin.schemas import (
    JobStatusResponse,
    PreprocessResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from src.admin.job_store import JobStatus
from src.pipeline import storage
from src.pipeline.scraping.law_scraper import scrape_law
from src.pipeline.preprocessing.cleaner import clean_raw

router = APIRouter()


# ── Background Task Wrapper ───────────────────────────────────────────────────

async def _scrape_and_save(job_id: str, law_id: str, law_name: str, url: str) -> None:
    """
    BackgroundTask olarak çalışır.
    scrape_law senkron → run_in_threadpool ile event loop bloklanmaz.
    0 madde dönen scrape job'ı failed yapar.
    """
    try:
        job_store.update_job(job_id, status=JobStatus.RUNNING)
        log.info(f"[Admin] Scraping başladı: job_id={job_id}, law_id={law_id}")

        raw_data = await run_in_threadpool(scrape_law, law_id, url, law_name)

        # 0 madde = selector kırık veya sayfa yapısı değişmiş
        if not raw_data.get("articles"):
            raise ValueError(
                f"Scraping tamamlandı fakat 0 madde döndü. "
                f"mevzuat.gov.tr sayfa yapısı değişmiş olabilir: {url}"
            )

        filename = storage.versioned_name(law_id, "raw")
        raw_path = storage.save_json(raw_data, storage.RAW_DIR, filename)

        job_store.update_job(job_id, status=JobStatus.DONE, raw_path=str(raw_path))
        log.info(
            f"[Admin] Scraping tamamlandı: job_id={job_id}, "
            f"madde_sayisi={len(raw_data['articles'])}, path={raw_path}"
        )

    except Exception as e:
        job_store.update_job(job_id, status=JobStatus.FAILED, error=str(e))
        log.error(f"[Admin] Scraping başarısız: job_id={job_id}, hata={e}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    summary="Kanun scraping başlat",
)
async def start_scrape(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_admin_key),
) -> ScrapeResponse:
    """
    Belirtilen kanun için scraping başlatır (background task).
    Aynı law_id tekrar gönderilirse yeni versiyonlu dosya oluşturulur, eski silinmez.
    """
    job = job_store.create_job(law_id=req.law_id, law_name=req.law_name)
    background_tasks.add_task(
        _scrape_and_save, job.id, req.law_id, req.law_name, req.url
    )
    log.info(f"[Admin] Job oluşturuldu: job_id={job.id}, law_id={req.law_id}")
    return ScrapeResponse(
        job_id=job.id,
        status=job.status,
        message=f"Scraping başlatıldı. Durumu takip etmek için GET /admin/scrape/{job.id}",
    )


@router.get(
    "/scrape",
    response_model=list[JobStatusResponse],
    summary="Tüm scraping joblarını listele",
)
async def list_scrape_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(verify_admin_key),
) -> list[JobStatusResponse]:
    """Son N scraping job'ını döndürür (varsayılan: 50)."""
    jobs = job_store.list_jobs(limit=limit)
    return [
        JobStatusResponse(
            id=j.id,
            law_id=j.law_id,
            law_name=j.law_name,
            status=j.status,
            raw_path=j.raw_path,
            clean_path=j.clean_path,
            error=j.error,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in jobs
    ]


@router.get(
    "/scrape/{job_id}",
    response_model=JobStatusResponse,
    summary="Job durumu ve verisi",
)
async def get_scrape_job(
    job_id: str,
    include_data: bool = Query(
        default=False,
        description="True ise raw ve clean JSON verisi yanıta eklenir",
    ),
    _: None = Depends(verify_admin_key),
) -> JobStatusResponse:
    """
    Job durumunu döndürür.
    include_data=true ile ham ve/veya temiz veri de yanıta eklenir.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' bulunamadı.")

    raw_data = None
    clean_data = None

    if include_data:
        if job.raw_path:
            try:
                raw_data = storage.load_json(job.raw_path)
            except Exception as e:
                log.warning(f"[Admin] raw_path okunamadı ({job.raw_path}): {e}")
        if job.clean_path:
            try:
                clean_data = storage.load_json(job.clean_path)
            except Exception as e:
                log.warning(f"[Admin] clean_path okunamadı ({job.clean_path}): {e}")

    return JobStatusResponse(
        id=job.id,
        law_id=job.law_id,
        law_name=job.law_name,
        status=job.status,
        raw_path=job.raw_path,
        clean_path=job.clean_path,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        raw_data=raw_data,
        clean_data=clean_data,
    )


@router.post(
    "/scrape/{job_id}/preprocess",
    response_model=PreprocessResponse,
    summary="Ham veriyi temizle ve normalize et",
)
async def preprocess_job(
    job_id: str,
    _: None = Depends(verify_admin_key),
) -> PreprocessResponse:
    """
    Scraping'i tamamlanmış bir job'ın ham verisini temizler.
    Temiz JSON versiyonlu dosyaya kaydedilir, ham dosya korunur.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' bulunamadı.")
    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=409,
            detail=f"Job henüz tamamlanmadı (status={job.status.value}). Scraping bitmeden preprocessing başlatılamaz.",
        )
    if not job.raw_path:
        raise HTTPException(status_code=409, detail="Ham veri dosyası bulunamadı.")

    try:
        raw_data = await run_in_threadpool(storage.load_json, job.raw_path)
        clean_data = await run_in_threadpool(clean_raw, raw_data)

        filename = storage.versioned_name(job.law_id, "clean")
        clean_path = storage.save_json(clean_data, storage.CLEAN_DIR, filename)

        job_store.update_job(job_id, clean_path=str(clean_path))
        log.info(
            f"[Admin] Preprocessing tamamlandı: job_id={job_id}, "
            f"madde_sayisi={clean_data.get('article_count')}, path={clean_path}"
        )

        return PreprocessResponse(
            job_id=job_id,
            status=job.status,
            clean_path=str(clean_path),
            article_count=clean_data.get("article_count"),
        )

    except Exception as e:
        log.error(f"[Admin] Preprocessing başarısız: job_id={job_id}, hata={e}")
        raise HTTPException(status_code=500, detail=f"Preprocessing hatası: {str(e)}")
