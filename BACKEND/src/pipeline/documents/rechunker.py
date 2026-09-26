"""
src/pipeline/documents/rechunker.py — Chunk Sinir Kaydirma, Bolme ve Birlestirme
=================================================================================
shift_boundary : Iki bitisik chunk arasindaki siniri kaydirma
split_chunk    : Bir chunk'i iki parcaya bolme
merge_chunks   : Iki ardisik chunk'i birlestirme

Tum metin operasyonlari full_text kaynaği uzerinden yapilir (string concat YOKSUN),
bu sayede round-trip tutarliligi (split+merge sonrasi bit-bit esit metin) garantilenir.
"""

import logging
import uuid
from typing import Tuple, Optional

from fastapi import HTTPException

from src.pipeline.documents import doc_store
from src.pipeline.documents.doc_store import ChunkRecord

MIN_CHUNK_CHARS = 20  # Bolme/kaydirma sonrasi izin verilen minimum chunk uzunlugu

log = logging.getLogger("LawAgent.Rechunker")


# ── Ortak Yardimci ─────────────────────────────────────────────────────────────

def _require_full_text_and_offsets(doc_id: str, filename: str) -> str:
    """full_text yoksa 409 firlatir, yoksa full_text dondurur."""
    full_text = doc_store.get_full_text(doc_id)
    if full_text is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{filename}' belgesi full_text olmadan indexlenmis (eski belge). "
                "Bu islem icin belgeyi silin ve yeniden yukleyin."
            ),
        )
    return full_text


def _require_chunk(doc_id: str, chunk_index: int) -> ChunkRecord:
    chunk = doc_store.get_chunk_by_index(doc_id, chunk_index)
    if chunk is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chunk[{chunk_index}] bulunamadi (doc_id={doc_id})",
        )
    if chunk.start_char is None or chunk.end_char is None:
        raise HTTPException(
            status_code=409,
            detail=f"Chunk[{chunk_index}] ofset bilgisi yok (eski belge). Yeniden yukleyin.",
        )
    return chunk


# ── shift_boundary ─────────────────────────────────────────────────────────────

def shift_boundary(
    doc_id: str,
    boundary_index: int,
    new_offset: int,
) -> Tuple[ChunkRecord, ChunkRecord]:
    """
    Chunk[boundary_index] ile Chunk[boundary_index+1] arasindaki siniri kaydirır.

    Izin verilen aralik (mantikli kisit):
    - lower: chunk[N-1].start_char + 1  (yoksa 0 — belge basi)
    - upper: chunk[N+2].end_char   - 1  (yoksa len(full_text) — belge sonu)
    Bu kural, N-1 veya N+2 numarali chunk'lar tamamen sifirlanamazken,
    N ve N+1 numaraları daha agresif sekilde yeniden boyutlanabilir.

    Ek kontrol: new_text_n ve new_text_n1'in MIN_CHUNK_CHARS (20) karakter icermesi zorunlu.
    """
    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")

    full_text = _require_full_text_and_offsets(doc_id, record.filename)

    chunk_n  = _require_chunk(doc_id, boundary_index)
    chunk_n1 = _require_chunk(doc_id, boundary_index + 1)

    # Kisit hesapla
    chunk_prev = doc_store.get_chunk_by_index(doc_id, boundary_index - 1)
    chunk_next = doc_store.get_chunk_by_index(doc_id, boundary_index + 2)

    if chunk_prev and chunk_prev.start_char is not None:
        lower_bound = chunk_prev.start_char + 1
    else:
        lower_bound = 0  # Belge basi

    if chunk_next and chunk_next.end_char is not None:
        upper_bound = chunk_next.end_char - 1
    else:
        upper_bound = len(full_text)  # Belge sonu

    if not (lower_bound <= new_offset <= upper_bound):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Gecersiz new_offset={new_offset}. "
                f"Izin verilen aralik: [{lower_bound}, {upper_bound}]."
            ),
        )

    # Yeni metinleri full_text'ten kes
    new_text_n  = full_text[chunk_n.start_char : new_offset]
    new_text_n1 = full_text[new_offset : chunk_n1.end_char]

    if len(new_text_n.strip()) < MIN_CHUNK_CHARS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Yeni sinir chunk[{boundary_index}]'i {len(new_text_n.strip())} karaktere "
                f"dusuruyor (minimum {MIN_CHUNK_CHARS})."
            ),
        )
    if len(new_text_n1.strip()) < MIN_CHUNK_CHARS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Yeni sinir chunk[{boundary_index+1}]'i {len(new_text_n1.strip())} karaktere "
                f"dusuruyor (minimum {MIN_CHUNK_CHARS})."
            ),
        )

    updated_n = doc_store.update_chunk(
        doc_id=doc_id,
        chunk_index=boundary_index,
        new_text=new_text_n,
        new_start_char=chunk_n.start_char,
        new_end_char=new_offset,
        manually_edited=True,
        qdrant_point_id=chunk_n.qdrant_point_id,
    )
    updated_n1 = doc_store.update_chunk(
        doc_id=doc_id,
        chunk_index=boundary_index + 1,
        new_text=new_text_n1,
        new_start_char=new_offset,
        new_end_char=chunk_n1.end_char,
        manually_edited=True,
        qdrant_point_id=chunk_n1.qdrant_point_id,
    )

    log.info(
        f"[Rechunker] shift_boundary: doc={doc_id}, boundary={boundary_index}, "
        f"new_offset={new_offset}, "
        f"chunk[{boundary_index}]={len(new_text_n)}ch, "
        f"chunk[{boundary_index+1}]={len(new_text_n1)}ch"
    )
    return updated_n, updated_n1


# ── split_chunk ───────────────────────────────────────────────────────────────

def split_chunk(
    doc_id: str,
    chunk_index: int,
    split_offset: int,
) -> Tuple[ChunkRecord, ChunkRecord]:
    """
    Chunk[chunk_index]'i split_offset noktasindan iki parcaya boler.
    split_offset: full_text icindeki karakter pozisyonu (chunk.start_char < split_offset < chunk.end_char)

    Islem:
    1. Eski chunk SQLite'tan silinir (qdrant_point_id geri alinir)
    2. Sonraki tum chunk_index'ler +1 kaydirilir
    3. Iki yeni chunk eklenir: A=[start_char, split_offset), B=[split_offset, end_char)
    4. Qdrant: eski point silinir, 2 yeni point upsert edilir (caller tarafindan)

    Doner: (chunk_a, chunk_b) — SQLite'a yazilmis hali
    """
    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")

    full_text = _require_full_text_and_offsets(doc_id, record.filename)
    chunk = _require_chunk(doc_id, chunk_index)

    # Aralik dogrulamasi
    if not (chunk.start_char < split_offset < chunk.end_char):
        raise HTTPException(
            status_code=422,
            detail=(
                f"split_offset={split_offset} chunk[{chunk_index}] araliginin "
                f"disinda: [{chunk.start_char}, {chunk.end_char}]."
            ),
        )

    text_a = full_text[chunk.start_char : split_offset]
    text_b = full_text[split_offset : chunk.end_char]

    if len(text_a.strip()) < MIN_CHUNK_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Bolme sonrasi A parcasi {len(text_a.strip())} karakter (minimum {MIN_CHUNK_CHARS}).",
        )
    if len(text_b.strip()) < MIN_CHUNK_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Bolme sonrasi B parcasi {len(text_b.strip())} karakter (minimum {MIN_CHUNK_CHARS}).",
        )

    old_point_id = doc_store.delete_chunk_by_index(doc_id, chunk_index)

    # Sonraki chunk'larin index'ini +1 kaydir (yeni bosluk ac)
    doc_store.shift_chunk_indices(doc_id, from_index=chunk_index + 1, delta=1)

    # Iki yeni chunk ekle
    point_id_a = str(uuid.uuid4())
    point_id_b = str(uuid.uuid4())

    chunk_a = doc_store.insert_chunk(
        doc_id=doc_id,
        chunk_index=chunk_index,
        chunk_text=text_a,
        start_char=chunk.start_char,
        end_char=split_offset,
        qdrant_point_id=point_id_a,
        manually_edited=True,
    )
    chunk_b = doc_store.insert_chunk(
        doc_id=doc_id,
        chunk_index=chunk_index + 1,
        chunk_text=text_b,
        start_char=split_offset,
        end_char=chunk.end_char,
        qdrant_point_id=point_id_b,
        manually_edited=True,
    )

    log.info(
        f"[Rechunker] split_chunk: doc={doc_id}, index={chunk_index}, "
        f"split_offset={split_offset}, old_point={old_point_id}, "
        f"new_points=[{point_id_a}, {point_id_b}]"
    )
    return chunk_a, chunk_b, old_point_id


# ── merge_chunks ───────────────────────────────────────────────────────────────

def merge_chunks(
    doc_id: str,
    chunk_index_a: int,
    chunk_index_b: int,
) -> Tuple[ChunkRecord, str, str]:
    """
    Chunk[chunk_index_a] ve Chunk[chunk_index_b]'yi birlestirir.
    Sadece ardisik chunk'lar birlestirilir (chunk_index_b == chunk_index_a + 1).

    Birlesmis metin: full_text[a.start_char : b.end_char]
    (string concat KULLANILMAZ — round-trip tutarliligi icin)

    Islem:
    1. Her iki chunk SQLite'tan silinir (point_id'leri alinir)
    2. Sonraki chunk'larin index'i -1 kaydirilir
    3. Yeni birlesik chunk eklenir (chunk_index_a konumuna)
    4. Qdrant: 2 eski point silinir, 1 yeni upsert edilir (caller tarafindan)

    Doner: (merged_chunk, old_point_id_a, old_point_id_b)
    """
    if chunk_index_b != chunk_index_a + 1:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Sadece ardisik chunk'lar birlestirilebilir. "
                f"chunk_index_b ({chunk_index_b}) != chunk_index_a + 1 ({chunk_index_a + 1})."
            ),
        )

    record = doc_store.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadi: {doc_id}")

    full_text = _require_full_text_and_offsets(doc_id, record.filename)
    chunk_a = _require_chunk(doc_id, chunk_index_a)
    chunk_b = _require_chunk(doc_id, chunk_index_b)

    # Metin full_text'ten kes (concat DEGIL)
    merged_text = full_text[chunk_a.start_char : chunk_b.end_char]

    MAX_MERGE_CHARS = 8000
    warning_text = None
    if len(merged_text) > MAX_MERGE_CHARS:
        warning_text = (
            f"Birlesmis chunk {len(merged_text)} karakter — "
            f"embedding model limiti ({MAX_MERGE_CHARS}) asiliyor. "
            "Embedding kalitesi dusebilir."
        )
        log.warning(f"[Rechunker] merge_chunks: {warning_text}")

    old_point_id_a = doc_store.delete_chunk_by_index(doc_id, chunk_index_a)
    old_point_id_b = doc_store.delete_chunk_by_index(doc_id, chunk_index_b)

    # chunk_index_b'den sonrakileri -1 kaydir
    doc_store.shift_chunk_indices(doc_id, from_index=chunk_index_b + 1, delta=-1)

    new_point_id = str(uuid.uuid4())
    merged_chunk = doc_store.insert_chunk(
        doc_id=doc_id,
        chunk_index=chunk_index_a,
        chunk_text=merged_text,
        start_char=chunk_a.start_char,
        end_char=chunk_b.end_char,
        qdrant_point_id=new_point_id,
        manually_edited=True,
    )

    log.info(
        f"[Rechunker] merge_chunks: doc={doc_id}, "
        f"merged=[{chunk_index_a},{chunk_index_b}], "
        f"old_points=[{old_point_id_a}, {old_point_id_b}], new_point={new_point_id}"
    )
    return merged_chunk, old_point_id_a, old_point_id_b, warning_text
