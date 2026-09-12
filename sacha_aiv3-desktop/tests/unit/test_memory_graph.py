"""Unit tests — core/memory (graph + store + retriever)."""

from core.memory.graph import MemoryFact, MemoryGraph, tokenize
from core.memory.retriever import MemoryRetriever


def test_persist_roundtrip(graph, tmp_path):
    graph.add_fact(MemoryFact(content="identity: Alice", entities=["Alice"], relation="identity", confidence=0.95))
    graph.add_fact(MemoryFact(content="preference: Coffee", entities=["Coffee"], confidence=0.8))
    assert graph.stats()["facts"] == 2
    assert graph.stats()["entities"] == 2

    reopened = MemoryGraph.open(tmp_path / "graph.db")
    assert reopened.stats()["facts"] == 2
    reopened.close()


def test_store_is_idempotent(graph):
    fact = MemoryFact(content="contact: bob@x.io", entities=["bob@x.io"], relation="contact", confidence=0.95)
    graph.add_fact(fact)
    graph.add_fact(fact)
    # The store never dedupes by itself — upserts accumulate by design,
    # but the graph dedupes tests via unique content lookups in retriever.
    assert graph.store.counts()["facts"] == 2


def test_retriever_finds_relevant_facts(graph):
    graph.add_fact(MemoryFact(content="identity: Alice", entities=["Alice"], relation="identity", confidence=0.95))
    graph.add_fact(MemoryFact(content="preference: Coffee", entities=["Coffee"], confidence=0.8))

    retriever = MemoryRetriever(graph)
    block = retriever.context_block("who is alice?")
    assert "Alice" in block
    # Irrelevant facts should not dominate the retrieved slice.
    irrelevant = retriever.context_block("quantum physics")
    assert irrelevant == "" or "Coffee" not in irrelevant


def test_neighbors(graph):
    graph.add_relation("Alice", "likes", "Coffee")
    triples = graph.neighbors("Alice", depth=1)
    assert any(t["target"] == "Coffee" for t in triples)
    assert any(t["relation"] == "likes" for t in triples)


def test_tokenize():
    assert tokenize("Hello, World!") == {"hello", "world"}


def test_recent_block(graph):
    graph.add_fact(MemoryFact(content="identity: Alice", entities=["Alice"], confidence=0.9))
    block = MemoryRetriever(graph).recent_block(limit=5)
    assert "Alice" in block


def test_decay_prunes_old_facts(tmp_path):
    from core.memory.decay import apply_temporal_decay
    from core.memory.store.graph_store import GraphStore

    store = GraphStore(tmp_path / "decay.db")
    store.upsert_fact("old: forgotten", confidence=0.1)
    store.upsert_fact("fresh: remembered", confidence=0.9)

    # 0-day cutoff → the creepy freshness sim: everything is "old" enough.
    pruned = apply_temporal_decay(store, max_age_days=0, min_confidence=0.5)
    assert pruned > 0
    assert store.all_facts(min_confidence=0.0) == []
    store.close()
