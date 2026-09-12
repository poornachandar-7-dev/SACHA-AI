"""
core/memory/decay.py — (planned→MVP) fact decay & conflict resolution.

Three cheap decay policies keep long-term memory trustworthy:

- temporal: old facts lose confidence over time
- access: facts nobody touches slowly fade
- conflict: duplicate facts merge and can be pruned

Run ``apply_temporal_decay`` on boot and periodically (the boostrap wires a
background loop). All policies are pure functions over :class:`GraphStore`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from core.memory.store.graph_store import GraphStore

logger = logging.getLogger(__name__)


def apply_temporal_decay(
    store: GraphStore,
    max_age_days: int = 120,
    min_confidence: float = 0.15,
    dry_run: bool = False,
) -> int:
    """Reduce confidence of facts older than ``max_age_days``; prune below floor.

    Returns the number of facts pruned. ``dry_run`` reports without deleting.
    """
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    old_facts = store.all_facts(min_confidence=0.0, limit=10000)
    pruned = 0
    for fact in old_facts:
        created = fact.get("created_at") or ""
        if created >= cutoff:
            continue
        confidence = float(fact.get("confidence", 0.5))
        decayed = confidence * 0.5  # one half-life
        if not dry_run:
            if decayed < min_confidence:
                store.delete_fact(fact["id"])
                pruned += 1
            else:
                store.set_fact_confidence(fact["id"], decayed)
    if pruned:
        logger.info("temporal decay pruned %d aged fact(s)", pruned)
    return pruned


def merge_duplicates(store: GraphStore, dry_run: bool = False) -> int:
    """Merge facts whose content is identical, keeping highest confidence."""
    facts = store.all_facts(min_confidence=0.0, limit=10000)
    by_content: dict[str, list[dict]] = {}
    for fact in facts:
        by_content.setdefault(fact["content"], []).append(fact)
    removed = 0
    for content, group in by_content.items():
        if len(group) < 2:
            continue
        keep = max(group, key=lambda f: float(f.get("confidence", 0.0)))
        for dup in group:
            if dup["id"] == keep["id"]:
                continue
            if not dry_run:
                store.delete_fact(dup["id"])
            removed += 1
    return removed


async def decay_loop(
    store: GraphStore,
    stop_event: asyncio.Event,
    interval_seconds: int = 86_400,  # daily
    max_age_days: int = 120,
) -> None:
    """Background task running decay policies on an interval."""
    logger.info("memory decay loop started (every %ds)", interval_seconds)
    while not stop_event.is_set():
        try:
            pruned = apply_temporal_decay(store, max_age_days=max_age_days)
            merged = merge_duplicates(store)
            if pruned or merged:
                logger.info("decay pass: pruned=%d merged=%d", pruned, merged)
        except Exception:
            logger.exception("memory decay pass failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue
    logger.info("memory decay loop stopped")
