"""
src/admin/job_store.py — SQLite Tabanlı Kalıcı Job Kaydı
=========================================================
Process restart'ta job geçmişi kaybolmaz.
Thread-safe: threading.Lock + check_same_thread=False.

NOT: Gelecekte uvicorn --workers >1 deploy için PRAGMA journal_mode=WAL ekleyin.
"""

import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# DB dosyası BACKEND/ altında
_DB_PATH = Path(__file__).resolve().parent.parent.parent / "jobs.db"

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


# ── Enum & Dataclass ─────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class JobRecord:
    id: str
    law_id: str
    law_name: str
    status: JobStatus
    raw_path: Optional[str] = None
    clean_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _create_table(_conn)
    return _conn


def _create_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            law_id      TEXT NOT NULL,
            law_name    TEXT NOT NULL,
            status      TEXT NOT NULL,
            raw_path    TEXT,
            clean_path  TEXT,
            error       TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.commit()


def _row_to_record(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        law_id=row["law_id"],
        law_name=row["law_name"],
        status=JobStatus(row["status"]),
        raw_path=row["raw_path"],
        clean_path=row["clean_path"],
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_job(law_id: str, law_name: str) -> JobRecord:
    """Yeni bir job kaydı oluşturur ve döndürür."""
    record = JobRecord(
        id=str(uuid.uuid4()),
        law_id=law_id,
        law_name=law_name,
        status=JobStatus.PENDING,
    )
    with _lock:
        conn = _get_conn()
        conn.execute(
            """INSERT INTO jobs
               (id, law_id, law_name, status, raw_path, clean_path, error, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.id, record.law_id, record.law_name, record.status.value,
             record.raw_path, record.clean_path, record.error,
             record.created_at, record.updated_at),
        )
        conn.commit()
    return record


def get_job(job_id: str) -> Optional[JobRecord]:
    """Job ID ile kaydı döndürür. Bulunamazsa None."""
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_record(row) if row else None


def update_job(job_id: str, **fields) -> None:
    """
    Verilen alanları günceller. updated_at otomatik set edilir.
    Kullanım: update_job(job_id, status="running", raw_path="/path/to/file.json")
    """
    allowed = {"status", "raw_path", "clean_path", "error"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = _now()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [job_id]

    with _lock:
        conn = _get_conn()
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
        conn.commit()


def list_jobs(limit: int = 50) -> list[JobRecord]:
    """Son N job'ı oluşturulma tarihine göre azalan sırada döndürür."""
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_record(r) for r in rows]
