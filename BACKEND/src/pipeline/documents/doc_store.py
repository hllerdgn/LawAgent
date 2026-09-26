"""
src/pipeline/documents/doc_store.py - SQLite tabanli sirket belgesi kayit modulu
"""

import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple

_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "jobs.db"
_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


@dataclass
class DocumentRecord:
    id: str
    filename: str
    file_type: str  # pdf | docx | txt
    status: str     # processing | indexed | failed
    chunk_count: int = 0
    document_id: str = ""
    file_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ChunkRecord:
    id: int
    doc_id: str
    chunk_index: int
    chunk_text: str
    char_count: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    manually_edited: bool = False
    qdrant_point_id: Optional[str] = None  # index'ten bagimsiz Qdrant point UUID


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _create_table(_conn)
        _migrate_schema(_conn)
    return _conn


def _create_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id          TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            file_type   TEXT NOT NULL,
            status      TEXT NOT NULL,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            document_id TEXT NOT NULL,
            file_path   TEXT,
            error       TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id          TEXT NOT NULL,
            chunk_index     INTEGER NOT NULL,
            chunk_text      TEXT NOT NULL,
            char_count      INTEGER NOT NULL,
            start_char      INTEGER,
            end_char        INTEGER,
            manually_edited INTEGER NOT NULL DEFAULT 0,
            qdrant_point_id TEXT,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(doc_id, chunk_index)"
    )
    conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Mevcut veritabanina eksik kolonlari ekler (idempotent)."""
    # documents tablosuna full_text kolonu
    existing_doc_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()
    }
    if "full_text" not in existing_doc_cols:
        conn.execute("ALTER TABLE documents ADD COLUMN full_text TEXT")

    # document_chunks tablosuna yeni kolonlar
    existing_chunk_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(document_chunks)").fetchall()
    }
    if "start_char" not in existing_chunk_cols:
        conn.execute("ALTER TABLE document_chunks ADD COLUMN start_char INTEGER")
    if "end_char" not in existing_chunk_cols:
        conn.execute("ALTER TABLE document_chunks ADD COLUMN end_char INTEGER")
    if "manually_edited" not in existing_chunk_cols:
        conn.execute(
            "ALTER TABLE document_chunks ADD COLUMN manually_edited INTEGER NOT NULL DEFAULT 0"
        )
    if "qdrant_point_id" not in existing_chunk_cols:
        conn.execute("ALTER TABLE document_chunks ADD COLUMN qdrant_point_id TEXT")
    conn.commit()


def _row_to_record(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        id=row["id"],
        filename=row["filename"],
        file_type=row["file_type"],
        status=row["status"],
        chunk_count=row["chunk_count"],
        document_id=row["document_id"],
        file_path=row["file_path"],
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_chunk(row: sqlite3.Row) -> ChunkRecord:
    keys = row.keys() if hasattr(row, 'keys') else []
    return ChunkRecord(
        id=row["id"],
        doc_id=row["doc_id"],
        chunk_index=row["chunk_index"],
        chunk_text=row["chunk_text"],
        char_count=row["char_count"],
        start_char=row["start_char"],
        end_char=row["end_char"],
        manually_edited=bool(row["manually_edited"]),
        qdrant_point_id=row["qdrant_point_id"] if "qdrant_point_id" in (row.keys() if hasattr(row, 'keys') else []) else None,
    )


def create_document(filename: str, file_type: str, document_id: str, file_path: Optional[str] = None) -> DocumentRecord:
    record = DocumentRecord(
        id=str(uuid.uuid4()),
        filename=filename,
        file_type=file_type,
        status="processing",
        document_id=document_id,
        file_path=file_path,
    )
    with _lock:
        conn = _get_conn()
        conn.execute(
            """INSERT INTO documents
               (id, filename, file_type, status, chunk_count, document_id, file_path, error, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.id, record.filename, record.file_type, record.status,
             record.chunk_count, record.document_id, record.file_path,
             record.error, record.created_at, record.updated_at),
        )
        conn.commit()
    return record


def get_document(doc_id: str) -> Optional[DocumentRecord]:
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return _row_to_record(row) if row else None


def get_document_by_document_id(document_id: str) -> Optional[DocumentRecord]:
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
    return _row_to_record(row) if row else None


def update_document(doc_id: str, **fields) -> None:
    allowed = {"status", "chunk_count", "file_path", "error"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [doc_id]
    with _lock:
        conn = _get_conn()
        conn.execute(f"UPDATE documents SET {set_clause} WHERE id = ?", values)
        conn.commit()


def delete_document(doc_id: str) -> bool:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cur.rowcount > 0


# ── Full Text CRUD ────────────────────────────────────────────────────────────

def save_full_text(doc_id: str, text: str) -> None:
    """Parser ciktisini (ham belge metni) documents tablosuna yazar."""
    with _lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE documents SET full_text = ?, updated_at = ? WHERE id = ?",
            (text, _now(), doc_id),
        )
        conn.commit()


def get_full_text(doc_id: str) -> Optional[str]:
    """Belgenin ham metnini dondurur. Eski belgeler icin None."""
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT full_text FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return row["full_text"] if row else None


# ── Chunk CRUD ────────────────────────────────────────────────────────────────

def save_chunks(
    doc_id: str,
    chunks: List[str],
    offsets: Optional[List[Tuple[int, int]]] = None,
) -> None:
    """
    Chunk metinlerini SQLite'a yazar. Her chunk icin UUID4 qdrant_point_id uretir.
    offsets: [(start_char, end_char), ...] — yeni belgeler icin saglanir.
    """
    if not chunks:
        return
    has_offsets = offsets and len(offsets) == len(chunks)
    rows = []
    for idx, text in enumerate(chunks):
        start = offsets[idx][0] if has_offsets else None
        end = offsets[idx][1] if has_offsets else None
        point_id = str(uuid.uuid4())
        rows.append((doc_id, idx, text, len(text), start, end, point_id))

    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
        conn.executemany(
            """INSERT INTO document_chunks
               (doc_id, chunk_index, chunk_text, char_count, start_char, end_char, qdrant_point_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()


def get_chunks(doc_id: str, limit: int = 50, offset: int = 0) -> tuple:
    """doc_id'e gore sayfalanmis chunk listesi dondurur. -> (chunks, total)"""
    with _lock:
        conn = _get_conn()
        total = conn.execute(
            "SELECT COUNT(*) FROM document_chunks WHERE doc_id = ?", (doc_id,)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT id, doc_id, chunk_index, chunk_text, char_count,
                      start_char, end_char, manually_edited, qdrant_point_id
               FROM document_chunks WHERE doc_id = ?
               ORDER BY chunk_index ASC LIMIT ? OFFSET ?""",
            (doc_id, limit, offset),
        ).fetchall()
    return [_row_to_chunk(r) for r in rows], total


def get_all_chunks(doc_id: str) -> List[ChunkRecord]:
    """Tum chunk'lari sirali dondurur (sayfalama yok — rechunker icin)."""
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            """SELECT id, doc_id, chunk_index, chunk_text, char_count,
                      start_char, end_char, manually_edited, qdrant_point_id
               FROM document_chunks WHERE doc_id = ?
               ORDER BY chunk_index ASC""",
            (doc_id,),
        ).fetchall()
    return [_row_to_chunk(r) for r in rows]


def get_chunk_by_index(doc_id: str, chunk_index: int) -> Optional[ChunkRecord]:
    """Tek bir chunk'i index numarasina gore getirir."""
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            """SELECT id, doc_id, chunk_index, chunk_text, char_count,
                      start_char, end_char, manually_edited, qdrant_point_id
               FROM document_chunks WHERE doc_id = ? AND chunk_index = ?""",
            (doc_id, chunk_index),
        ).fetchone()
    return _row_to_chunk(row) if row else None


def update_chunk(
    doc_id: str,
    chunk_index: int,
    new_text: str,
    new_start_char: int,
    new_end_char: int,
    manually_edited: bool = True,
    qdrant_point_id: Optional[str] = None,
) -> Optional[ChunkRecord]:
    """Tek bir chunk'in metnini, ofsetlerini ve opsiyonel point_id'sini gunceller."""
    with _lock:
        conn = _get_conn()
        if qdrant_point_id is not None:
            conn.execute(
                """UPDATE document_chunks
                   SET chunk_text = ?, char_count = ?, start_char = ?, end_char = ?,
                       manually_edited = ?, qdrant_point_id = ?
                   WHERE doc_id = ? AND chunk_index = ?""",
                (new_text, len(new_text), new_start_char, new_end_char,
                 int(manually_edited), qdrant_point_id, doc_id, chunk_index),
            )
        else:
            conn.execute(
                """UPDATE document_chunks
                   SET chunk_text = ?, char_count = ?, start_char = ?, end_char = ?,
                       manually_edited = ?
                   WHERE doc_id = ? AND chunk_index = ?""",
                (new_text, len(new_text), new_start_char, new_end_char,
                 int(manually_edited), doc_id, chunk_index),
            )
        conn.commit()
    return get_chunk_by_index(doc_id, chunk_index)


def insert_chunk(
    doc_id: str,
    chunk_index: int,
    chunk_text: str,
    start_char: Optional[int],
    end_char: Optional[int],
    qdrant_point_id: Optional[str] = None,
    manually_edited: bool = False,
) -> ChunkRecord:
    """Yeni bir chunk kaydi olusturur. Caller shift_chunk_indices cagirmaktan sorumludur."""
    point_id = qdrant_point_id or str(uuid.uuid4())
    with _lock:
        conn = _get_conn()
        conn.execute(
            """INSERT INTO document_chunks
               (doc_id, chunk_index, chunk_text, char_count, start_char, end_char,
                manually_edited, qdrant_point_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, chunk_index, chunk_text, len(chunk_text),
             start_char, end_char, int(manually_edited), point_id),
        )
        conn.commit()
    result = get_chunk_by_index(doc_id, chunk_index)
    assert result is not None
    return result


def delete_chunk_by_index(doc_id: str, chunk_index: int) -> Optional[str]:
    """Tek chunk'i SQLite'tan siler; Qdrant'ta silinmesi gereken point_id'yi dondurur."""
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT qdrant_point_id FROM document_chunks WHERE doc_id = ? AND chunk_index = ?",
            (doc_id, chunk_index),
        ).fetchone()
        point_id = row["qdrant_point_id"] if row else None
        conn.execute(
            "DELETE FROM document_chunks WHERE doc_id = ? AND chunk_index = ?",
            (doc_id, chunk_index),
        )
        conn.commit()
    return point_id


def shift_chunk_indices(doc_id: str, from_index: int, delta: int) -> None:
    """
    from_index'ten buyuk veya esit chunk_index degerlerini 'delta' kadar kaydirir.
    delta > 0: split sonrasi (+1), delta < 0: merge sonrasi (-1).
    """
    with _lock:
        conn = _get_conn()
        if delta > 0:
            # Buyukten kucuge guncelle (cakismayi onle)
            conn.execute(
                """UPDATE document_chunks
                   SET chunk_index = chunk_index + ?
                   WHERE doc_id = ? AND chunk_index >= ?""",
                (delta, doc_id, from_index),
            )
        else:
            # Kucukten buyuge guncelle
            conn.execute(
                """UPDATE document_chunks
                   SET chunk_index = chunk_index + ?
                   WHERE doc_id = ? AND chunk_index >= ?""",
                (delta, doc_id, from_index),
            )
        conn.commit()


def delete_chunks(doc_id: str) -> int:
    """Belge silindiginde ilgili chunk'lari temizler. Silinen satir sayisi doner."""
    with _lock:
        conn = _get_conn()
        cur = conn.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
        conn.commit()
        return cur.rowcount


def list_documents() -> list:
    with _lock:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    return [_row_to_record(r) for r in rows]
