"""
src/admin/routes.py — Admin Scraping Router
============================================
Endpoint'ler:
  POST /admin/scrape                      → scraping başlat
  GET  /admin/scrape                      → tüm jobları listele
  GET  /admin/scrape/{job_id}             → job durumu + opsiyonel veri
  POST /admin/scrape/{job_id}/preprocess  → preprocessing çalıştır
"""

from pathlib import Path
from typing import Any

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
from src.pipeline.scraping.law_scraper import scrape_law, build_pdf_url
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
        curr = job_store.get_job(job_id)
        if curr and curr.status == JobStatus.CANCELED:
            log.info(f"[Admin] Job başlatılmadan önce iptal edilmiş: job_id={job_id}")
            return

        job_store.update_job(job_id, status=JobStatus.RUNNING)
        log.info(f"[Admin] Scraping başladı: job_id={job_id}, law_id={law_id}")

        raw_data = await run_in_threadpool(scrape_law, law_id, url, law_name)

        curr = job_store.get_job(job_id)
        if curr and curr.status == JobStatus.CANCELED:
            log.info(f"[Admin] Job scrape sırasında iptal edildi: job_id={job_id}")
            return

        # 0 madde = selector kırık veya sayfa yapısı değişmiş
        if not raw_data.get("articles"):
            raise ValueError(
                f"Scraping tamamlandı fakat 0 madde döndü. "
                f"mevzuat.gov.tr sayfa yapısı değişmiş olabilir: {url}"
            )

        filename = storage.versioned_name(law_id, "raw")
        raw_path = storage.save_json(raw_data, storage.RAW_DIR, filename)

        curr = job_store.get_job(job_id)
        if curr and curr.status == JobStatus.CANCELED:
            try:
                Path(raw_path).unlink(missing_ok=True)
            except Exception:
                pass
            return

        job_store.update_job(job_id, status=JobStatus.DONE, raw_path=str(raw_path))
        log.info(
            f"[Admin] Scraping tamamlandı: job_id={job_id}, "
            f"madde_sayisi={len(raw_data['articles'])}, path={raw_path}"
        )

    except Exception as e:
        curr = job_store.get_job(job_id)
        if curr and curr.status == JobStatus.CANCELED:
            return
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
    
    target_url = req.url
    if not target_url:
        target_url = build_pdf_url(req.law_id)
        
    background_tasks.add_task(
        _scrape_and_save, job.id, req.law_id, req.law_name, target_url
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
            parent_job_id=j.parent_job_id,
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
        parent_job_id=job.parent_job_id,
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
        print(f"[RAW] Ham verideki madde sayısı: {len(raw_data.get('articles', []))}")

        clean_data = await run_in_threadpool(clean_raw, raw_data)
        print(f"[CP1] clean_raw döndürdü: {len(clean_data['articles'])} madde")

        print(f"[CP2] save_json'a giden madde sayısı: {len(clean_data['articles'])}")
        filename = storage.versioned_name(job.law_id, "clean")
        clean_path = storage.save_json(clean_data, storage.CLEAN_DIR, filename)

        reloaded = storage.load_json(clean_path)
        print(f"[CP3] diskten geri okunan madde sayısı: {len(reloaded['articles'])}")

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
            duplicate_lines_removed=clean_data.get("duplicate_lines_removed", 0),
            dropped_article_count=clean_data.get("dropped_article_count", 0),
            dropped_article_nos=clean_data.get("dropped_article_nos", []),
        )

    except Exception as e:
        log.error(f"[Admin] Preprocessing başarısız: job_id={job_id}, hata={e}")
        raise HTTPException(status_code=500, detail=f"Preprocessing hatası: {str(e)}")


@router.delete(
    "/scrape/{job_id}",
    summary="Scraping job'ını ve ilişkili dosyalarını sil",
)
async def delete_scrape_job(
    job_id: str,
    _: None = Depends(verify_admin_key),
) -> dict[str, Any]:
    """
    Belirtilen job'ı ve varsa ilişkili raw/clean dosyalarını siler.
    Yalnızca 'done', 'failed' veya 'canceled' durumundaki işler silinebilir.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' bulunamadı.")

    if job.status not in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELED):
        raise HTTPException(
            status_code=409,
            detail=f"Job silinemez (status={job.status.value}). Yalnızca 'done', 'failed' veya 'canceled' durumundaki işler silinebilir.",
        )

    deleted_files: list[str] = []
    for path_str in (job.raw_path, job.clean_path):
        if path_str:
            p = Path(path_str)
            if p.is_file():
                try:
                    p.unlink(missing_ok=True)
                    deleted_files.append(str(p))
                except Exception as e:
                    log.warning(f"[Admin] Dosya silinemedi ({path_str}): {e}")

    job_store.delete_job(job_id)
    log.info(f"[Admin] Job silindi: job_id={job_id}, silinen_dosyalar={deleted_files}")
    return {
        "success": True,
        "message": f"Job {job_id} ve ilişkili dosyalar silindi.",
        "deleted_files": deleted_files,
    }


@router.post(
    "/scrape/{job_id}/cancel",
    response_model=JobStatusResponse,
    summary="Çalışan veya bekleyen job'ı iptal et",
)
async def cancel_scrape_job(
    job_id: str,
    _: None = Depends(verify_admin_key),
) -> JobStatusResponse:
    """
    Çalışan veya bekleyen ('pending'|'running') scraping job'ını iptal eder.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' bulunamadı.")

    if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Job iptal edilemez (status={job.status.value}). Yalnızca 'pending' veya 'running' işler iptal edilebilir.",
        )

    job_store.update_job(job_id, status=JobStatus.CANCELED)
    updated = job_store.get_job(job_id)
    log.info(f"[Admin] Job iptal edildi: job_id={job_id}")

    return JobStatusResponse(
        id=updated.id,
        law_id=updated.law_id,
        law_name=updated.law_name,
        status=updated.status,
        raw_path=updated.raw_path,
        clean_path=updated.clean_path,
        error=updated.error,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        parent_job_id=updated.parent_job_id,
    )


@router.post(
    "/scrape/{job_id}/retry",
    response_model=ScrapeResponse,
    summary="Başarısız veya iptal edilmiş job'ı yeni ID ile tekrar dene",
)
async def retry_scrape_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_admin_key),
) -> ScrapeResponse:
    """
    Sadece 'failed' veya 'canceled' olan job'lar için YENİ bir job_id ile yeni kayıt oluşturur.
    Eski id parent_job_id olarak saklanır.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' bulunamadı.")

    if job.status not in (JobStatus.FAILED, JobStatus.CANCELED):
        raise HTTPException(
            status_code=409,
            detail=f"Job tekrar denenemez (status={job.status.value}). Yalnızca 'failed' veya 'canceled' işler tekrar denenebilir.",
        )

    new_job = job_store.create_job(
        law_id=job.law_id,
        law_name=job.law_name,
        parent_job_id=job.id,
    )

    target_url = build_pdf_url(job.law_id)
    background_tasks.add_task(
        _scrape_and_save, new_job.id, new_job.law_id, new_job.law_name, target_url
    )
    log.info(f"[Admin] Job retry başlatıldı: parent_id={job.id}, new_job_id={new_job.id}")

    return ScrapeResponse(
        job_id=new_job.id,
        status=new_job.status,
        message=f"Job yeniden başlatıldı (yeni id: {new_job.id}).",
    )
