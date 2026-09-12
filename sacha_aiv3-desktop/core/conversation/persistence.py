"""
core/conversation/persistence.py — persists sessions to SQLite on shutdown.

Writes are small and infrequent, so this is a thin sqlite3 wrapper executed
via ``asyncio.to_thread`` to keep the event loop non-blocking.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BOOT_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SessionStore:
    """SQLite persistence for conversation sessions."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_BOOT_SCHEMA)
        self._conn.commit()
        self._lock = asyncio.Lock()

    async def save_session(self, session) -> None:
        """Upsert a session + its messages (idempotent for repeats)."""
        sid = session.session_id
        now = _now()

        def _write() -> None:
            self._conn.execute(
                """INSERT OR REPLACE INTO sessions (id, started_at, updated_at, summary)
                   VALUES (?, ?, ?, ?)""",
                (sid, now, now, ""),
            )
            existing = {r["content"] for r in self._conn.execute(
                "SELECT content FROM messages WHERE session_id = ?", (sid,)
            ).fetchall()}
            for msg in session.messages():
                if msg.content in existing:
                    continue
                self._conn.execute(
                    "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (sid, msg.role, msg.content, msg.created_at),
                )
                existing.add(msg.content)
            self._conn.commit()

        async with self._lock:
            await asyncio.to_thread(_write)

    async def load_latest(self, limit_messages: int = 50) -> dict[str, Any] | None:
        """Most recent session's messages (for conversation restore)."""

        def _read() -> dict[str, Any] | None:
            row = self._conn.execute("SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1").fetchone()
            if not row:
                return None
            msgs = [dict(r) for r in self._conn.execute(
                "SELECT role, content, created_at FROM messages WHERE session_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (row["id"], limit_messages),
            ).fetchall()]
            msgs.reverse()
            return {"session_id": row["id"], "messages": msgs}

        async with self._lock:
            return await asyncio.to_thread(_read)

    async def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        def _read() -> list[dict[str, Any]]:
            return [dict(r) for r in self._conn.execute(
                "SELECT id, started_at, updated_at, summary FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()]

        async with self._lock:
            return await asyncio.to_thread(_read)

    def close(self) -> None:
        self._conn.close()

    async def aclose(self) -> None:
        await asyncio.to_thread(self.close)
