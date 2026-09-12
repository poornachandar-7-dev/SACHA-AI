"""
core/reply/composer.py — assembles a reply from provider + memory + tools.

Flow per user turn:

1. Classify intent (OmniRouter) — a tool call can short-circuit to a tool.
2. Build the prompt (system/SOUL + memory subgraph + recent history).
3. Generate through the fallback chain (streaming or full).
4. Update the session and hand the exchange to the fact extractor queue.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from core.conversation.session import Session
from core.memory.extractor import ConversationExchange, FactExtractor
from core.memory.graph import MemoryGraph
from core.reply.context import ContextBuilder
from core.router.fallback import FallbackChain
from core.router.omni_router import OmniRouter
from core.tools.registry import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    text: str
    provider: str = ""
    tool: str | None = None
    duration_ms: float = 0.0
    token_estimate: int = 0
    streamed: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


class ReplyComposer:
    """Orchestrates one user turn end-to-end."""

    def __init__(
        self,
        router: OmniRouter,
        fallback: FallbackChain,
        context_builder: ContextBuilder,
        session: Session,
        graph: MemoryGraph | None = None,
        extractor: FactExtractor | None = None,
        tools: ToolRegistry | None = None,
        extractor_queue: asyncio.Queue | None = None,
        auto_tools: bool = True,
    ) -> None:
        self.router = router
        self.fallback = fallback
        self.context_builder = context_builder
        self.session = session
        self.graph = graph
        self.extractor = extractor
        self.tools = tools
        self.extractor_queue = extractor_queue or asyncio.Queue()
        self.auto_tools = auto_tools

    # -- public API ---------------------------------------------------------
    async def reply(self, user_text: str, **kwargs: Any) -> ChatResult:
        """Full (non-streamed) reply, tools allowed."""
        started = time.perf_counter()
        self.session.add("user", user_text)

        tool = await self._maybe_run_tool(user_text)
        if tool is not None:
            result = tool
            self.session.add("assistant", result.output)
            self._queue_extraction(user_text, result.output)
            return ChatResult(
                text=result.output,
                provider="tool",
                tool=tool.name,
                duration_ms=(time.perf_counter() - started) * 1000,
            )

        messages = self.context_builder.build_messages(user_text, **kwargs)
        preferred = self.router.choose_provider(user_text)
        text, provider = await self.fallback.complete(preferred, messages, **kwargs)
        self.session.add("assistant", text)
        self._queue_extraction(user_text, text)
        return ChatResult(
            text=text,
            provider=provider,
            duration_ms=(time.perf_counter() - started) * 1000,
            token_estimate=_estimate_tokens(text),
        )

    async def stream(self, user_text: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        """Yield event dicts: ``{type: token|done|error, ...}``."""
        started = time.perf_counter()
        self.session.add("user", user_text)

        tool = await self._maybe_run_tool(user_text)
        if tool is not None:
            self.session.add("assistant", tool.output)
            self._queue_extraction(user_text, tool.output)
            yield {"type": "token", "text": tool.output, "provider": "tool", "tool": tool.name}
            yield {"type": "done", "result": tool.output, "provider": "tool"}
            return

        messages = self.context_builder.build_messages(user_text, **kwargs)
        preferred = self.router.choose_provider(user_text)
        collected: list[str] = []
        provider_used = ""
        try:
            async for token, provider in self.fallback.stream(preferred, messages, **kwargs):
                collected.append(token)
                provider_used = provider
                yield {"type": "token", "text": token, "provider": provider}
        except Exception as exc:
            yield {"type": "error", "message": str(exc)}
            return

        full = "".join(collected)
        self.session.add("assistant", full)
        self._queue_extraction(user_text, full)
        yield {
            "type": "done",
            "provider": provider_used,
            "duration_ms": (time.perf_counter() - started) * 1000,
            "token_estimate": _estimate_tokens(full),
        }

    # -- internals ------------------------------------------------------------
    async def _maybe_run_tool(self, user_text: str) -> ToolResult | None:
        """Handle explicit ``!toolname args`` calls and known tool categories."""
        if self.tools is None:
            return None
        text = user_text.strip()
        if text.startswith("!"):
            parts = text[1:].split(None, 1)
            name, args = parts[0], (parts[1] if len(parts) > 1 else "")
            return await self.tools.invoke_text(name, args)
        if self.auto_tools:
            intent = self.router.classify(text)
            if intent.category == "tool" and intent.tool_hint and self.tools.has(intent.tool_hint):
                # Only auto-fire harmless read-only tools.
                return await self.tools.invoke_text(intent.tool_hint, text)
        return None

    def _queue_extraction(self, user_text: str, assistant_text: str) -> None:
        if self.extractor is None or self.graph is None:
            return
        try:
            self.extractor_queue.put_nowait(
                ConversationExchange(user_text=user_text, assistant_text=assistant_text)
            )
        except asyncio.QueueFull:  # pragma: no cover
            logger.warning("extractor queue full; dropping exchange")

    @staticmethod
    def to_json(result: ChatResult) -> str:
        return json.dumps(
            {
                "text": result.text,
                "provider": result.provider,
                "tool": result.tool,
                "duration_ms": round(result.duration_ms, 1),
                "token_estimate": result.token_estimate,
            },
            ensure_ascii=False,
        )


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (ASCII ~1 token/4 chars)."""
    return max(1, len(text) // 4)
