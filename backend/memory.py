"""
SACHA — Memory module.
Stores chat history in SQLite.no semantic search
"""
import sqlite3
import os
from datetime import datetime, timezone

# Use __file__ to correctly resolve the path relative to this script
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "sacha.db")

def _get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    return conn

def save_message(role: str, content: str):
    conn = _get_connection()
    conn.execute(
        "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

def get_history(limit: int = 20) -> list:
    conn = _get_connection()
    rows = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    
    # reverse so oldest comes first
    return [{"role": r, "content": c} for r, c in reversed(rows)]