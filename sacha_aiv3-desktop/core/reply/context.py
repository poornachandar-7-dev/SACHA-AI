"""
core/reply/context.py — builds the prompt context (graph subgraph + recent).

The system prompt is the personality (SOUL.md) plus, when relevant, the
memory subgraph block and the tool catalogue. Provider calls receive only:
system + recent session window + the current user message — nothing else.
"""

from __future__ import annotations

from typing import Any

from core.conversation.session import Session
from core.memory.retriever import MemoryRetriever
from personality.loader import PersonalityLoader


class ContextBuilder:
    """Assemble the message list that gets sent to a provider."""

    def __init__(
        self,
        personality: PersonalityLoader,
        session: Session | None = None,
        retriever: MemoryRetriever | None = None,
    ) -> None:
        self.personality = personality
        self.session = session
        self.retriever = retriever

    def system_instructions(self, extra: str = "") -> str:
        """SOUL.md + memory guidance + any dynamic additions."""
        parts = [self.personality.system_prompt()]
        if self.retriever is not None:
            parts.append(
                "You have long-term memory. A 'Memory from past conversations' "
                "block, when present in this prompt, is ground truth about the user."
            )
        if extra:
            parts.append(extra)
        return "\n\n".join(parts)

    def build_messages(
        self,
        user_text: str,
        *,
        history_n: int | None = 12,
        memory_facts: int = 6,
        tool_catalogue: str = "",
        extra: str = "",
    ) -> list[dict[str, Any]]:
        """Full OpenAI-style message list for one user turn."""
        system = self.system_instructions(extra)
        memory_block = ""
        if self.retriever is not None and memory_facts > 0:
            memory_block = self.retriever.context_block(user_text, limit=memory_facts)
            if memory_block:
                system = f"{system}\n\n{memory_block}"
        if tool_catalogue:
            system = f"{system}\n\n{tool_catalogue}"

        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        if self.session is not None:
            messages.extend(self.session.as_dicts(history_n))
        messages.append({"role": "user", "content": user_text})
        return messages
