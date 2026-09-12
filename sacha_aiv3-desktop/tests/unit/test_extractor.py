"""Unit tests — core/memory/extractor.py (background fact extraction)."""

import asyncio

from core.memory.extractor import ConversationExchange, FactExtractor


def test_identity_extraction(graph):
    extractor = FactExtractor(graph)
    facts = extractor.extract_from_exchange("My name is Alice")
    assert any(f.relation == "identity" for f in facts)


def test_preference_extraction(graph):
    extractor = FactExtractor(graph)
    facts = extractor.extract_from_exchange("I love coffee and dark chocolate")
    assert any(f.relation == "preference" for f in facts)


def test_reminder_extraction(graph):
    extractor = FactExtractor(graph)
    facts = extractor.extract_from_text("remind me to take out the trash")
    assert any(f.relation == "reminder" for f in facts)


def test_min_confidence_filter(graph):
    extractor = FactExtractor(graph, min_confidence=0.99)
    facts = extractor.extract_from_exchange("remind me to take out the trash")
    assert facts == []  # all patterns are below 0.99


def test_consume_loop_writes_facts(graph):

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait(ConversationExchange("My name is Bob and I like hiking"))
    stop = asyncio.Event()

    async def go():
        task = asyncio.create_task(FactExtractor(graph).consume(queue, stop))
        await asyncio.wait_for(queue.join(), timeout=2.0)
        stop.set()
        await task

    asyncio.run(go())
    assert graph.stats()["facts"] >= 1
    assert any("Bob" in str(f["content"]) for f in graph.store.all_facts())
