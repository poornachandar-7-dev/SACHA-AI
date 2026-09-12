"""
core/memory/graph.py — graph store: nodes = entities, edges = relations.

Wraps :class:`GraphStore` (durable) with a networkx in-memory graph for
cheap traversal, and defines :class:`MemoryFact` — the unit the background
fact extractor writes and the retriever reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from core.memory.store.graph_store import GraphStore

_WORD_RE = re.compile(r"[a-zA-Z0-9']+")


@dataclass
class MemoryFact:
    """A single extracted memory statement."""

    content: str
    entities: list[str] = field(default_factory=list)
    relation: str | None = None
    confidence: float = 0.5
    source: str = "conversation"

    def to_store(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "entities": self.entities,
            "relation": self.relation,
            "confidence": self.confidence,
            "source": self.source,
        }


class MemoryGraph:
    """Durable + traversable long-term memory."""

    def __init__(self, store: GraphStore | None = None) -> None:
        self.store = store
        self._g: nx.DiGraph = nx.DiGraph()

    @classmethod
    def open(cls, db_path: str | Path | None = None) -> MemoryGraph:
        """Open (or create) the graph, loading any existing data."""
        store = GraphStore(db_path) if db_path is not None else None
        graph = cls(store=store)
        if store is not None:
            graph.reload()
        return graph

    # -- persistence ---------------------------------------------------------
    def reload(self) -> None:
        """Rebuild the in-memory graph from the store (used at boot)."""
        self._g = nx.DiGraph()
        if self.store is None:
            return
        for row in self.store.all_facts(min_confidence=0.0, limit=5000):
            fact_id = row["id"]
            self._g.add_node(f"fact_{fact_id}", kind="fact", text=row["content"], data=row["id"])
            for name in (row.get("entities_json") or row.get("entities") or []):
                self._g.add_node(name, kind="entity")
                self._g.add_edge(name, f"fact_{fact_id}", relation="mentions")

    def persist(self) -> None:
        """Sync any in-memory-only changes to the store."""
        # Writes always go through add_fact/add_entity in this codebase, so
        # persist() is only needed if callers mutate the graph directly.
        if self.store:
            pass  # no-op: both layers stay in sync by construction

    # -- mutations -------------------------------------------------------------
    def add_fact(self, fact: MemoryFact) -> int | None:
        """Insert a fact and its entity nodes/edges. Returns store row id."""
        fact_id = None
        if self.store is not None:
            fact_id = self.store.upsert_fact(**fact.to_store())
            self._g.add_node(f"fact_{fact_id}", kind="fact", text=fact.content)
        for name in fact.entities:
            self.add_entity(name)
            if fact_id is not None:
                self._g.add_edge(name, f"fact_{fact_id}", relation="mentions")
        return fact_id

    def add_entity(self, name: str, kind: str = "generic") -> int | None:
        self._g.add_node(name, kind=kind)
        if self.store is not None:
            return self.store.upsert_entity(name, kind=kind)
        return None

    def add_relation(self, source: str, relation: str, target: str) -> int | None:
        self._g.add_edge(source, target, relation=relation)
        if self.store is not None:
            return self.store.add_relation(source, relation, target)
        return None

    # -- queries ----------------------------------------------------------------
    def has_fact(self, content: str) -> bool:
        if self.store is not None:
            return any(f["content"] == content for f in self.store.search_facts(content, limit=50))
        return any(
            data.get("text") == content
            for _, data in self._g.nodes(data=True)
            if data.get("kind") == "fact"
        )

    def facts_for_query(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if self.store is not None:
            return self.store.search_facts(query, limit=limit)
        return []

    def neighbors(self, entity: str, depth: int = 1) -> list[dict[str, Any]]:
        if self.store is not None:
            return self.store.neighbors(entity, depth=depth)
        out: list[dict[str, Any]] = []
        if entity not in self._g:
            return out
        for neighbor in nx.single_source_shortest_path(self._g, entity, cutoff=depth):
            if neighbor == entity:
                continue
            out.append({"source": entity, "relation": "->", "target": neighbor})
        return out

    def entity_names(self) -> list[str]:
        return [n for n, d in self._g.nodes(data=True) if d.get("kind") == "entity"]

    def stats(self) -> dict[str, int]:
        if self.store is not None:
            return self.store.counts()
        return {
            "entities": sum(1 for _, d in self._g.nodes(data=True) if d.get("kind") == "entity"),
            "relations": self._g.number_of_edges(),
            "facts": sum(1 for _, d in self._g.nodes(data=True) if d.get("kind") == "fact"),
        }

    def close(self) -> None:
        if self.store is not None:
            self.store.close()


def tokenize(text: str) -> set[str]:
    """Lowercased alpha-numeric tokens for keyword overlap scoring."""
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 2}
