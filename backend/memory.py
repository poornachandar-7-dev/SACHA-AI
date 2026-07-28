"""
SACHA — Memory module.

Provides a small, safe wrapper around an on-disk SQLite DB to store chat messages.
Improvements:
- safer path handling and env override
- connection context manager and PRAGMA tuning
- row factory -> dict-like rows
- explicit init_db() and small helper functions
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_env_db_path = os.environ.get("SACHA_DB_PATH", "").strip()
DB_PATH = Path(_env_db_path) if _env_db_path else Path(__file__).resolve().parents[1] / "database" / "sacha.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
"""

# PRAGMA statements we want on each connection
_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
]


def _ensure_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _get_connection():
    """
    Yields a sqlite3.Connection configured with useful PRAGMAs and row factory.
    The connection is always closed when the context exits.
    """
    _ensure_dir()
    # Per-request connection: safe for multi-threaded web servers if you open/close per call.
    # detect_types can be enabled if you want typed columns in the future.
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for p in _PRAGMAS:
            cur.execute(p)
        # Ensure schema exists on first use
        cur.executescript(_SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    Ensure the database and schema exist. This can be called at app startup.
    """
    with _get_connection():
        # schema creation is handled in _get_connection
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_message(role: str, content: str) -> int:
    """
    Save a message and return the inserted row id.
    """
    if not role:
        raise ValueError("role must be non-empty")
    if content is None:
        raise ValueError("content must not be None")

    with _get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, _now_iso()),
        )
        return cast_int(cur.lastrowid)


def get_history(limit: int = 20) -> List[Dict]:
    """
    Return the last `limit` messages as list of dicts, oldest first.
    Dict keys: id, role, content, timestamp
    """
    if limit <= 0:
        return []

    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    # rows are sqlite3.Row -> map to dict and reverse to oldest-first order
    return [dict(r) for r in reversed(rows)]


def clear_history() -> None:
    """Delete all messages (useful for tests or 'reset' behavior)."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM messages")


def delete_message(message_id: int) -> bool:
    """Delete a single message. Returns True if a row was deleted."""
    with _get_connection() as conn:
        cur = conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        return cur.rowcount > 0


def count_messages() -> int:
    """Return total number of stored messages."""
    with _get_connection() as conn:
        cur = conn.execute("SELECT COUNT(1) as c FROM messages")
        return int(cur.fetchone()["c"])


def get_messages_since(timestamp_iso: str) -> List[Dict]:
    """
    Return messages with timestamp greater than the provided ISO timestamp.
    Input must be an ISO 8601 string in UTC (e.g. produced by save_message).
    """
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, timestamp FROM messages WHERE timestamp > ? ORDER BY id ASC",
            (timestamp_iso,),
        ).fetchall()
    return [dict(r) for r in rows]


# small helper for typing
def cast_int(x: Optional[int]) -> int:
    return int(x or 0)