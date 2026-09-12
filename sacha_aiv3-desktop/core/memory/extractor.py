"""
core/memory/extractor.py — background fact-extraction task.

Runs on the asyncio loop without blocking the reply path. Every finished
conversation turn is queued here; a cheap pattern-matching extractor pulls
high-confidence facts (name, preferences, facts about the user, reminders)
and writes them into the graph. A better NLP/LLM extractor can replace the
patterns without touching the rest of the pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from core.memory.graph import MemoryFact, MemoryGraph

logger = logging.getLogger(__name__)


@dataclass
class ConversationExchange:
    """One user turn + the assistant's reply, ready for extraction."""

    user_text: str
    assistant_text: str = ""
    ts: str | None = None


# -- pattern catalog ----------------------------------------------------------
_PATTERNS: list[tuple[str, str, float]] = [
    # (regex, relation, confidence)
    (r"\bmy name is ([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b", "identity", 0.95),
    (r"\b(?:i'm|i am) called ([A-Z][a-z]+)\b", "identity", 0.9),
    (r"\bcall me ([A-Z][a-z]+)\b", "alias", 0.9),
    (r"\bmy email(?: address)? is ([\w.+-]+@[\w-]+\.[\w.]+)\b", "contact", 0.95),
    (r"\bmy phone(?: number)? is ([\d+\- ]{7,})\b", "contact", 0.9),
    (r"\bi (?:love|like|enjoy|adore) ([\w]+(?: [\w]+){0,3})\b", "preference", 0.75),
    (r"\bi (?:don't|do not) (?:love|like|enjoy) ([\w]+(?: [\w]+){0,3})\b", "aversion", 0.75),
    (r"\bi (?:work|am working) (?:at|for) ([A-Z][\w. ]+)\b", "work", 0.8),
    (r"\bi (?:live|living) in ([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b", "location", 0.75),
    (r"\bmy birthday is ([\w ,]+)\b", "birthday", 0.8),
    (r"\bi (?:want|would like|need) ([\w]+(?: [\w]+){0,4})\b", "desire", 0.6),
    (r"\bremind me (?:to|about) ([^,.]+)\b", "reminder", 0.65),
]

_ENTITY_WORDS_RE = re.compile(r"\b([A-Z][a-z]{2,})\b")


class FactExtractor:
    """Pattern-based fact extraction with a background consume loop."""

    def __init__(self, graph: MemoryGraph, min_confidence: float = 0.5) -> None:
        self.graph = graph
        self.min_confidence = min_confidence
        self.extracted = 0

    def extract_from_text(self, text: str) -> list[MemoryFact]:
        """Run patterns over one message; return qualifying :class:`MemoryFact`."""
        facts: list[MemoryFact] = []
        seen: set[str] = set()
        for pattern, relation, base_conf in _PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = match.group(1).strip()
                content = f"{relation}: {value}"
                if content in seen:
                    continue
                seen.add(content)
                entities = list(dict.fromkeys([value, *_ENTITY_WORDS_RE.findall(text)]))
                facts.append(
                    MemoryFact(
                        content=content,
                        entities=entities[:5],
                        relation=relation,
                        confidence=base_conf,
                    )
                )
        return facts

    def extract_from_exchange(
        self,
        user_text: str,
        assistant_text: str = "",
    ) -> list[MemoryFact]:
        found = self.extract_from_text(user_text or "")
        if assistant_text:
            found += self.extract_from_text(assistant_text)
        return [f for f in found if f.confidence >= self.min_confidence]

    async def consume(
        self,
        queue: asyncio.Queue[ConversationExchange],
        stop_event: asyncio.Event,
    ) -> None:
        """Background task: drain the queue and write facts into the graph."""
        logger.info("fact extractor started")
        while not stop_event.is_set():
            try:
                exchange = await asyncio.wait_for(queue.get(), timeout=0.5)
            except TimeoutError:
                continue
            try:
                facts = self.extract_from_exchange(exchange.user_text, exchange.assistant_text)
                for fact in facts:
                    fact_id = self.graph.add_fact(fact)
                    if fact_id is not None:
                        self.extracted += 1
                        logger.debug("memory fact #%s: %s", fact_id, fact.content)
            except Exception:  # never let extraction break the reply path
                logger.exception("fact extraction failed")
            finally:
                queue.task_done()
        logger.info("fact extractor stopped (%d facts extracted)", self.extracted)
