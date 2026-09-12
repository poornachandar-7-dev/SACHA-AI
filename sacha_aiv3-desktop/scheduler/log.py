"""
scheduler/log.py — execution log (success / failure / retry).

A tiny SQLite append-only log: when a job fired, whether it succeeded, and
any error text. Kept separate from the memory graphs so scheduler noise never
pollutes conversation memory.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    fired_at TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_job_runs_job ON job_runs(job_id);
"""


class JobLog:
    """Execution log for scheduled jobs."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else Path.cwd() / "data" / "scheduler.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record(self, job_id: str, fired_at: str | None = None, status: str = "ok", error: str | None = None) -> int:
        fired = fired_at or datetime.now(UTC).isoformat()
        cur = self._conn.execute(
            "INSERT INTO job_runs (job_id, fired_at, status, error) VALUES (?, ?, ?, ?)",
            (job_id, fired, status, error),
        )
        self._conn.commit()
        return cur.lastrowid

    def last(self, job_id: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        if job_id:
            rows = self._conn.execute(
                "SELECT * FROM job_runs WHERE job_id = ? ORDER BY id DESC LIMIT ?", (job_id, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM job_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def failures(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM job_runs WHERE status != 'ok' ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
