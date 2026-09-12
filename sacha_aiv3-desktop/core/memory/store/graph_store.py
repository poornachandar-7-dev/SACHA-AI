"""
core/memory/store/graph_store.py — SQLite-backed graph persistence.

Stores three relationally-connected tables:

- ``entities`` — nodes: people, places, concepts, the user…
- ``relations`` — typed edges: (User) -likes-> (Coffee)
- ``facts`` — the extracted natural-language statements, tagged with the
  entity names they mention and a decaying confidence score.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'generic',
    props TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES entities(id),
    relation TEXT NOT NULL,
    target_id INTEGER NOT NULL REFERENCES entities(id),
    weight REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    entities_json TEXT NOT NULL DEFAULT '[]',
    relation TEXT,
    confidence REAL NOT NULL DEFAULT 0.5,
    source TEXT NOT NULL DEFAULT 'conversation',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class GraphStore:
    """SQLite persistence layer for the entity/relation/fact graph."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- entities ----------------------------------------------------------
    def upsert_entity(self, name: str, kind: str = "generic", props: dict | None = None) -> int:
        name = self._normalize(name)
        existing = self._conn.execute(
            "SELECT id, props FROM entities WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            merged = {**(json.loads(existing["props"]) if existing["props"] else {}), **(props or {})}
            self._conn.execute(
                "UPDATE entities SET props = ?, kind = ?, updated_at = datetime('now') WHERE id = ?",
                (json.dumps(merged), kind, existing["id"]),
            )
            self._conn.commit()
            return existing["id"]
        cur = self._conn.execute(
            "INSERT INTO entities (name, kind, props) VALUES (?, ?, ?)",
            (name, kind, json.dumps(props or {})),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_entity(self, name: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM entities WHERE name = ?", (self._normalize(name),)
        ).fetchone()
        return self._row(row)

    def search_entities(self, term: str, limit: int = 25) -> list[dict[str, Any]]:
        like = f"%{term.lower()}%"
        rows = self._conn.execute(
            "SELECT * FROM entities WHERE lower(name) LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (like, limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def add_relation(self, source: str, relation: str, target: str, weight: float = 1.0) -> int:
        src_id = self.upsert_entity(source)
        tgt_id = self.upsert_entity(target)
        existing = self._conn.execute(
            "SELECT id FROM relations WHERE source_id=? AND relation=? AND target_id=?",
            (src_id, relation, tgt_id),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = self._conn.execute(
            "INSERT INTO relations (source_id, relation, target_id, weight) VALUES (?, ?, ?, ?)",
            (src_id, relation, tgt_id, weight),
        )
        self._conn.commit()
        return cur.lastrowid

    def neighbors(self, entity_name: str, depth: int = 1) -> list[dict[str, Any]]:
        """Return ``{source, relation, target}`` triples within ``depth`` hops."""
        entity = self.get_entity(entity_name)
        if not entity:
            return []
        seen_ids: set[tuple[int, int]] = set()
        frontier: set[int] = {entity["id"]}
        triples: list[dict[str, Any]] = []
        for _ in range(max(1, depth)):
            next_frontier: set[int] = set()
            placeholders = ",".join("?" for _ in frontier)
            rows = self._conn.execute(
                f"""SELECT e1.name AS source, r.relation AS relation, e2.name AS target,
                           e1.id AS s_id, e2.id AS t_id
                    FROM relations r
                    JOIN entities e1 ON e1.id = r.source_id
                    JOIN entities e2 ON e2.id = r.target_id
                    WHERE r.source_id IN ({placeholders}) OR r.target_id IN ({placeholders})""",
                (*frontier, *frontier),
            ).fetchall()
            for row in rows:
                pair = (row["s_id"], row["t_id"])
                if pair not in seen_ids:
                    triples.append(self._row(row))
                    seen_ids.add(pair)
                next_frontier.add(row["s_id"])
                next_frontier.add(row["t_id"])
            frontier = next_frontier - frontier
            if not frontier:
                break
        return triples

    def upsert_fact(
        self,
        content: str,
        entities: list[str] | None = None,
        relation: str | None = None,
        confidence: float = 1.0,
        source: str = "conversation",
    ) -> int:
        norm_entities = [self._normalize(e) for e in (entities or [])]
        cur = self._conn.execute(
            """INSERT INTO facts (content, entities_json, relation, confidence, source)
               VALUES (?, ?, ?, ?, ?)""",
            (content.strip(), json.dumps(norm_entities), relation, float(confidence), source),
        )
        # Register entities as nodes so the graph always stays connected.
        for name in norm_entities:
            self.upsert_entity(name)
        self._conn.commit()
        return cur.lastrowid

    def search_facts(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        import re as _re

        tokens = [
            _re.sub(r"[^a-z0-9']", "", t.lower())
            for t in query.split()
            if len(_re.sub(r"[^a-z0-9']", "", t.lower())) > 2
        ]
        clause = " OR ".join("lower(content) LIKE ?" for t in (tokens or [""]))
        params = [f"%{t}%" for t in (tokens or [""])]
        rows = self._conn.execute(
            f"SELECT * FROM facts WHERE {clause} ORDER BY confidence DESC, updated_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def facts_by_entities(self, entity_names: list[str], limit: int = 20) -> list[dict[str, Any]]:
        """Facts that mention any of ``entity_names`` (via LIKE on the JSON)."""
        if not entity_names:
            return []
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE " + " OR ".join("entities_json LIKE ?" for _ in entity_names)
            + " ORDER BY confidence DESC, updated_at DESC LIMIT ?",
            (*[f"%{self._normalize(n)}%" for n in entity_names], limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def all_facts(self, min_confidence: float = 0.0, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE confidence >= ? ORDER BY updated_at DESC LIMIT ?",
            (min_confidence, limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def delete_fact(self, fact_id: int) -> None:
        self._conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self._conn.commit()

    def set_fact_confidence(self, fact_id: int, confidence: float) -> None:
        self._conn.execute(
            "UPDATE facts SET confidence = ?, updated_at = datetime('now') WHERE id = ?",
            (float(confidence), fact_id),
        )
        self._conn.commit()

    def counts(self) -> dict[str, int]:
        return {
            "entities": self._conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "relations": self._conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
            "facts": self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
        }

    # -- plumbing -----------------------------------------------------------
    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip()

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        d = dict(row)
        for key in ("props", "entities_json"):
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
