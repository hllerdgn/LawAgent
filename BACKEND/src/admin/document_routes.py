"""
src/admin/document_routes.py - Sirket Belgesi Yukleme & Yonetim Endpointleri
=============================================================================
Endpointler:
  POST   /admin/documents                     - Belge yukle (PDF/DOCX/TXT, max 10MB)
  GET    /admin/documents                     - Belge listesi
  GET    /admin/documents/{id}                - Tek belge detayi
  GET    /admin/documents/{id}/chunks         - Belge chunk'lari (sayfalanmis)
  DELETE /admin/documents/{id}               - Belge + vektorleri sil
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional
from math import ceil

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from src.admin.auth import verify_admin_key
from src.scope_checker import clear_route_cache
from src.pipeline.documents import doc_store
from src.pipeline.documents.parser import parse_document, chunk_generic
from src.pipeline.documents.rechunker import shift_boundary
from src.pipeline.documents.indexer import (
    delete_document_vectors,
    index_document,
    index_single_chunk,
    ensure_company_collection,
)

log = logging.getLogger("LawAgent.DocumentRoutes")

router = APIRouter()

# Yuklemeler icin dizin
_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "company_docs"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Kabul edilen MIME tipleri ve uzantilari
_ALLOWED_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}
_ALLOWED_EXT = {"pdf", "docx", "txt"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _slugify(text: str) -> str:
    """Dosya adini URL-safe slug'a cevir."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:64] or "document"


def _get_qdrant_and_embedder():
    """Retriever singleton'indan qdrant ve embedder al."""
    from src.generator import get_retriever
    retriever = get_retriever()
    return retriever.qdrant, retriever.embedder


def _get_company_collection() -> str:
    from config.settings import settings
    return settings.COMPANY_COLLECTION_NAME


# ── Background Task ──────────────────────────────────────────────────────────

async def _process_and_index(doc_id: str, file_path: str, file_type: str, document_id: str) -> None:
    """Parse -> Chunk (ofsetli) -> Embed -> Index pipeline (arka planda calisir)."""
    try:
        log.info(f"[DocumentRoutes] Isleme basladi: doc_id={doc_id}, file={file_path}")

        # 1. Parse -- ham metni al
        text = await run_in_threadpool(parse_document, file_path, file_type)
        if not text.strip():
            raise ValueError("Belgeden metin cikarilamadi.")

        # 2. Ham metni SQLite'a kaydet (sinir kaydirma icin gerekli)
        await run_in_threadpool(doc_store.save_full_text, doc_id, text)

        # 3. Chunk -- (chunk_text, start_char, end_char) tuple listesi
        chunk_tuples = chunk_generic(text)
        if not chunk_tuples:
            raise ValueError("Metinden chunk olusturulamadi.")

        chunk_texts = [t for t, _s, _e in chunk_tuples]
        chunk_offsets = [(s, e) for _t, s, e in chunk_tuples]

        # 4. Embed & Index (Qdrant)
        collection_name = _get_company_collection()
        qdrant, embedder = await run_in_threadpool(_get_qdrant_and_embedder)
        chunk_count = await run_in_threadpool(
            index_document, document_id, chunk_texts, embedder, qdrant, collection_name
        )

        # 5. Chunk metinlerini + ofsetleri SQLite'a yaz
        await run_in_threadpool(
            doc_store.save_chunks, doc_id, chunk_texts, chunk_offsets
        )

        # 6. Kaydi guncelle
        doc_store.update_document(doc_id, status="indexed", chunk_count=chunk_count)
        clear_route_cache()
        log.info(f"[DocumentRoutes] Indexleme tamamlandi: doc_id={doc_id}, chunk_count={chunk_count}")

    except Exception as e:
        log.error(f"[DocumentRoutes] Isleme hatasi: doc_id={doc_id}, hata={e}")
        doc_store.update_document(doc_id, status="failed", error=str(e)[:500])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/documents", summary="Sirket belgesi yukle", tags=["Documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: None = Depends(verify_admin_key),
):
    """
    PDF, DOCX veya TXT belge yukle.
    - Max 10 MB
    - Ayni belge (dosya adi slug) zaten varsa OVERWRITE edilir.
    """
    # 1. Format kontrolu
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    content_type = (file.content_type or "").split(";")[0].strip()
    if ext not in _ALLOWED_EXT and content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=422,
            detail=f"Desteklenmeyen format. Kabul edilen: PDF, DOCX, TXT. Gelen: .{ext} / {content_type}",
        )
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=422,
            detail=f"Desteklenmeyen uzanti: .{ext}. Kabul edilen: .pdf, .docx, .txt",
        )

    # 2. Boyut kontrolu (once icerigi oku)
    contents = await file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Dosya boyutu siniri asisdi ({len(contents)/1024/1024:.1f} MB). Max 10 MB.",
        )

    filename = file.filename or f"document.{ext}"
    document_id = _slugify(Path(filename).stem)
    collection_name = _get_company_collection()

    # 3. Overwrite: eski vektorleri sil, eski DB kaydini sil
    existing = doc_store.get_document_by_document_id(document_id)
    if existing:
        log.info(f"[DocumentRoutes] Overwrite: document_id='{document_id}', eski kayit siliniyor.")
        try:
            qdrant, _ = _get_qdrant_and_embedder()
            delete_document_vectors(document_id, qdrant, collection_name)
        except Exception as e:
            log.warning(f"[DocumentRoutes] Eski vektorler silinemedi: {e}")
        # Eski dosyayi sil
        if existing.file_path:
            try:
                Path(existing.file_path).unlink(missing_ok=True)
            except Exception:
                pass
        doc_store.delete_document(existing.id)

    # 4. Dosyayi kaydet
    save_path = _UPLOAD_DIR / f"{document_id}.{ext}"
    save_path.write_bytes(contents)

    # 5. DB kaydi olustur
    record = doc_store.create_document(
        filename=filename,
        file_type=ext,
        document_id=document_id,
        file_path=str(save_path),
    )

    # 6. Background task baslat
    background_tasks.add_task(_process_and_index, record.id, str(save_path), ext, document_id)

    return {
        "id": record.id,
        "document_id": document_id,
        "filename": filename,
        "file_type": ext,
        "status": "processing",
        "message": f"'{filename}' yuklendi, islem arka planda devam ediyor.",
    }


@router.get("/documents", summary="Belge listesi", tags=["Documents"])
async def list_documents(_: None = Depends(verify_admin_key)):
    """Yuklenmis tum sirket belgelerini listeler."""
    records = doc_store.list_documents()
    return {
        "documents": [
            {
                "id": r.id,
                "filename": r.filename,
                "file_type": r.file_type,
                "status": r.status,
                "chunk_count": r.chunk_count,
                "document_id": r.document_id,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "error": r.error,
            }
            for r in records
        ],
        "total": len(records),
    }


@router.get("/documents/{doc_id}", summary="Belge detayi", tags=["Documents"])
async def get_document(doc_id: str, _: None = Depends(verify_admin_key)):
    """Tek belge detayini dondurur."""
    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")
    return {
        "id": record.id,
        "filename": record.filename,
        "file_type": record.file_type,
        "status": record.status,
        "chunk_count": record.chunk_count,
        "document_id": record.document_id,
        "file_path": record.file_path,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "error": record.error,
    }


@router.delete("/documents/{doc_id}", summary="Belge sil", tags=["Documents"])
async def delete_document(doc_id: str, _: None = Depends(verify_admin_key)):
    """
    Belgeyi ve company_corpus'taki vektorlerini siler.
    """
    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")

    collection_name = _get_company_collection()

    # 1. Vektorleri sil
    try:
        qdrant, _ = _get_qdrant_and_embedder()
        delete_document_vectors(record.document_id, qdrant, collection_name)
    except Exception as e:
        log.warning(f"[DocumentRoutes] Vektor silme hatasi (doc_id={doc_id}): {e}")

    # 2. SQLite chunk'larini sil (cascade)
    doc_store.delete_chunks(doc_id)

    # 3. Dosyayi sil
    if record.file_path:
        try:
            Path(record.file_path).unlink(missing_ok=True)
        except Exception as e:
            log.warning(f"[DocumentRoutes] Dosya silinemedi ({record.file_path}): {e}")

    # 4. DB kaydini sil
    doc_store.delete_document(doc_id)
    clear_route_cache()

    return {"status": "ok", "message": f"'{record.filename}' ve ilgili vektorler silindi."}


@router.get("/documents/{doc_id}/chunks", summary="Belge chunk listesi", tags=["Documents"])
async def get_document_chunks(
    doc_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Sayfa basi chunk sayisi"),
    offset: int = Query(default=0, ge=0, description="Atlanacak chunk sayisi"),
    _: None = Depends(verify_admin_key),
):
    """
    Belgeye ait chunk'lari chunk_index siralamasiyla dondurur.
    SQLite'ta kayit yoksa (eski belgeler) Qdrant'tan lazy migration yapar.
    Buyuk belgeler icin limit/offset sayfalama kullanin.
    """
    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")

    # ── SQLite'tan cek ──────────────────────────────────────────────────────
    _, sqlite_total = doc_store.get_chunks(doc_id, limit=1, offset=0)

    # ── Lazy Migration: SQLite bos ama belge indexed ise Qdrant'tan cek ────
    if sqlite_total == 0 and record.status == "indexed" and record.chunk_count > 0:
        log.info(
            f"[Chunks] doc_id={doc_id} — SQLite'ta chunk yok, "
            f"Qdrant'tan lazy migration baslatiyor (chunk_count={record.chunk_count})"
        )
        try:
            collection_name = _get_company_collection()
            qdrant, _ = await run_in_threadpool(_get_qdrant_and_embedder)
            from qdrant_client.http import models as qm
            # Qdrant'tan tum chunk'lari cek (scroll ile)
            all_points = []
            next_offset = None
            while True:
                result, next_offset = qdrant.scroll(
                    collection_name=collection_name,
                    scroll_filter=qm.Filter(
                        must=[qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=record.document_id),
                        )]
                    ),
                    limit=200,
                    offset=next_offset,
                    with_payload=True,
                    with_vectors=False,
                )
                all_points.extend(result)
                if next_offset is None:
                    break

            if all_points:
                # chunk_idx'e gore sirala
                all_points.sort(key=lambda p: p.payload.get("chunk_idx", 0))
                chunk_texts = [p.payload.get("text", "") for p in all_points]
                # SQLite'a yaz (lazy migration)
                await run_in_threadpool(doc_store.save_chunks, doc_id, chunk_texts)
                log.info(
                    f"[Chunks] Lazy migration tamamlandi: doc_id={doc_id}, "
                    f"{len(chunk_texts)} chunk SQLite'a yazildi"
                )
            else:
                log.warning(
                    f"[Chunks] doc_id={doc_id} — Qdrant'ta da chunk bulunamadi "
                    f"(collection={collection_name}, document_id={record.document_id})"
                )
        except Exception as e:
            log.warning(f"[Chunks] Lazy migration hatasi doc_id={doc_id}: {e}")

    # ── Son veriyi SQLite'tan cek ────────────────────────────────────────────    # ---- Son veriyi SQLite'tan cek ----
    chunks, total = doc_store.get_chunks(doc_id, limit=limit, offset=offset)
    return {
        "doc_id": doc_id,
        "filename": record.filename,
        "total": total,
        "limit": limit,
        "offset": offset,
        "pages": ceil(total / limit) if limit > 0 else 1,
        "has_offsets": any(c.start_char is not None for c in chunks),
        "chunks": [
            {
                "chunk_index": c.chunk_index,
                "chunk_text": c.chunk_text,
                "char_count": c.char_count,
                "start_char": c.start_char,
                "end_char": c.end_char,
                "manually_edited": c.manually_edited,
            }
            for c in chunks
        ],
    }


# -- Boundary Shift --

class BoundaryShiftRequest(BaseModel):
    boundary_index: int
    new_offset: int


@router.patch("/documents/{doc_id}/chunks/boundary", summary="Chunk sinirini kaydir", tags=["Documents"])
async def shift_chunk_boundary(
    doc_id: str,
    body: BoundaryShiftRequest,
    _: None = Depends(verify_admin_key),
):
    """
    Chunk[boundary_index] ile Chunk[boundary_index+1] arasindaki siniri yeni
    bir karakter ofseti ile kaydirip her iki chunk'i Qdrant'ta yeniden embed eder.
    Sadece 2 embedding cagrisi yapar (O(1) maliyet).
    """
    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")

    updated_n, updated_n1 = await run_in_threadpool(
        shift_boundary, doc_id, body.boundary_index, body.new_offset
    )

    try:
        collection_name = _get_company_collection()
        qdrant, embedder = await run_in_threadpool(_get_qdrant_and_embedder)
        await run_in_threadpool(
            index_single_chunk,
            record.document_id, updated_n.chunk_index, updated_n.chunk_text,
            embedder, qdrant, collection_name,
        )
        await run_in_threadpool(
            index_single_chunk,
            record.document_id, updated_n1.chunk_index, updated_n1.chunk_text,
            embedder, qdrant, collection_name,
        )
        log.info(
            f"[DocumentRoutes] Boundary shift Qdrant upsert tamamlandi: "
            f"doc_id={doc_id}, chunks=[{updated_n.chunk_index}, {updated_n1.chunk_index}]"
        )
    except Exception as e:
        log.error(f"[DocumentRoutes] Boundary shift Qdrant hatasi: {e}")
        raise HTTPException(
            status_code=500,
            detail="Sinir SQLite'ta guncellendi ancak Qdrant embed hatasi: " + str(e),
        )

    return {
        "status": "ok",
        "boundary_index": body.boundary_index,
        "new_offset": body.new_offset,
        "chunks": [
            {
                "chunk_index": updated_n.chunk_index,
                "chunk_text": updated_n.chunk_text,
                "char_count": updated_n.char_count,
                "start_char": updated_n.start_char,
                "end_char": updated_n.end_char,
                "manually_edited": updated_n.manually_edited,
            },
            {
                "chunk_index": updated_n1.chunk_index,
                "chunk_text": updated_n1.chunk_text,
                "char_count": updated_n1.char_count,
                "start_char": updated_n1.start_char,
                "end_char": updated_n1.end_char,
                "manually_edited": updated_n1.manually_edited,
            },
        ],
    }
