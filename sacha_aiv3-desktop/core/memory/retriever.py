"""
core/memory/retriever.py — pulls only the relevant subgraph into context.

Instead of resending the whole history, the retriever scores stored facts
against the current query (keyword overlap + graph neighbourhood) and emits
a small, human-readable context block for the prompt.
"""

from __future__ import annotations

from typing import Any

from core.memory.graph import MemoryGraph, tokenize


class MemoryRetriever:
    """Retrieve the small subgraph that matters for a given query."""

    def __init__(self, graph: MemoryGraph, default_facts: int = 6) -> None:
        self.graph = graph
        self.default_facts = default_facts

    def retrieve_facts(self, query: str, limit: int | None = None, include_graph_neighbors: bool = True) -> list[dict[str, Any]]:
        """Score facts by query-keyword overlap; enrich with graph neighbours."""
        limit = limit or self.default_facts
        query_tokens = tokenize(query)
        candidates: list[dict[str, Any]] = []

        if self.graph.store is not None:
            base = self.graph.store.search_facts(query, limit=max(limit * 4, 20))
            for fact in base:
                overlap = len(query_tokens & tokenize(fact["content"]))
                if overlap == 0:
                    # keep low-overlap candidates but rank them below
                    overlap = 0.1
                candidates.append({**fact, "_score": overlap * fact.get("confidence", 0.5)})
        else:
            candidates = self.graph.facts_for_query(query, limit=max(limit * 4, 20))

        # Graph-neighbourhood expansion: entities named in the query.
        if include_graph_neighbors and self.graph.store is not None:
            for name in sorted(self.graph.entity_names(), key=lambda s: -len(s)):
                if name.lower() not in query.lower():
                    continue
                triples = self.graph.store.neighbors(name, depth=1)
                related_names = {
                    t["target"] for t in triples if t["source"] == name
                } | {t["source"] for t in triples if t["target"] == name}
                for f in self.graph.store.facts_by_entities(list(related_names), limit=10):
                    candidates.append({**f, "_score": 0.4 * f.get("confidence", 0.5)})

        seen: set[int] = set()
        ranked: list[dict[str, Any]] = []
        for c in candidates:
            fid = c["id"]
            if fid in seen:
                continue
            seen.add(fid)
            ranked.append(c)
        ranked.sort(key=lambda c: c.get("_score", 0.0), reverse=True)
        return ranked[:limit]

    def context_block(self, query: str, limit: int | None = None) -> str:
        """Human-readable memory block ready to paste into the system prompt."""
        facts = self.retrieve_facts(query, limit=limit)
        if not facts:
            return ""
        lines = [f"- {f['content']}" for f in facts]
        return "Memory from past conversations:\n" + "\n".join(lines)

    def recent_block(self, limit: int = 8) -> str:
        """Most recent facts regardless of relevance (HUD memory panel)."""
        if self.graph.store is None:
            return ""
        facts = self.graph.store.all_facts(min_confidence=0.0, limit=limit)
        if not facts:
            return ""
        return "\n".join(f"- {f['content']}" for f in facts)
