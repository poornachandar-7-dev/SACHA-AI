"""
core/memory — graph-based long-term memory (V3's big upgrade).
"""

from core.memory.decay import (
    apply_temporal_decay,
    decay_loop,
    merge_duplicates,
)
from core.memory.extractor import ConversationExchange, FactExtractor
from core.memory.graph import MemoryFact, MemoryGraph, tokenize
from core.memory.retriever import MemoryRetriever

__all__ = [
    "apply_temporal_decay",
    "decay_loop",
    "merge_duplicates",
    "ConversationExchange",
    "FactExtractor",
    "MemoryFact",
    "MemoryGraph",
    "tokenize",
    "MemoryRetriever",
]
