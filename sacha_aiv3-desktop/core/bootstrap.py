"""
core/bootstrap.py — async event loop boot, wiring of all subsystems.

Builds the :class:`AppContext` — a single object holding every wired
subsystem. ``AppContext`` is passed around instead of using globals, and it
owns the background tasks (fact extractor, memory decay, schedulers, bridge
gateways) so shutdown cancels them in one place.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import Settings, get_settings
from core.conversation.persistence import SessionStore
from core.conversation.session import Session
from core.logging import get_logger, setup_logging
from core.memory.decay import decay_loop
from core.memory.extractor import ConversationExchange, FactExtractor
from core.memory.graph import MemoryGraph
from core.memory.retriever import MemoryRetriever
from core.providers.registry import ProviderRegistry
from core.reply.composer import ReplyComposer
from core.reply.context import ContextBuilder
from core.router.classifier import KeywordClassifier
from core.router.fallback import FallbackChain
from core.router.omni_router import OmniRouter
from core.tools.registry import ToolRegistry
from personality.loader import PersonalityLoader

logger = get_logger(__name__)


@dataclass
class AppContext:
    """Holds every wired subsystem. Passed around instead of globals."""

    settings: Settings
    provider_registry: ProviderRegistry | None = None
    omni_router: OmniRouter | None = None
    fallback: FallbackChain | None = None
    memory_graph: MemoryGraph | None = None
    fact_extractor: FactExtractor | None = None
    memory_retriever: MemoryRetriever | None = None
    tool_registry: ToolRegistry | None = None
    session: Session | None = None
    session_store: SessionStore | None = None
    personality: PersonalityLoader | None = None
    composer: ReplyComposer | None = None
    extractor_queue: asyncio.Queue[ConversationExchange] = field(default_factory=asyncio.Queue)
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    _background_tasks: set[asyncio.Task] = field(default_factory=set)

    def spawn_background(self, coro) -> asyncio.Task:
        """Track a background task so bootstrap can cancel it on shutdown."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def shutdown(self) -> None:
        logger.info("Shutting down: cancelling %d background task(s)", len(self._background_tasks))
        self.stop_event.set()
        for task in list(self._background_tasks):
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

        if self.session_store is not None and self.session is not None:
            try:
                await self.session_store.save_session(self.session)
                await self.session_store.aclose()
            except Exception:
                logger.exception("failed to persist session on shutdown")
        if self.memory_graph is not None:
            self.memory_graph.close()
        for provider in self.provider_registry.all() if self.provider_registry else []:
            try:
                await provider.close()
            except Exception:
                logger.debug("provider %s close failed", provider.name, exc_info=True)
        logger.info("SACHA engine stopped")

    def describe(self) -> dict[str, Any]:
        """Public snapshot for the HUD status bar."""
        return {
            "app": "SACHA V3",
            "settings": {
                "env": self.settings.env,
                "default_provider": self.settings.default_provider,
            },
            "router": self.omni_router.describe() if self.omni_router else {},
            "memory": self.memory_graph.stats() if self.memory_graph else {},
            "session": self.session.snapshot() if self.session is not None else {},
            "tools": [t["name"] for t in (self.tool_registry.describe_all() if self.tool_registry else [])],
        }


async def create_context(settings: Settings | None = None, *, data_dir: str | Path | None = None) -> AppContext:
    """Wire every subsystem and return a ready-to-use AppContext."""
    settings = settings or get_settings()
    if data_dir is not None:
        settings.data_dir = Path(data_dir)
        settings.chat_db_path = Path(data_dir) / "chat.db"
        settings.graph_db_path = Path(data_dir) / "graph.db"
        settings.preferences_path = Path(data_dir) / "preferences.json"
    settings.ensure_dirs()
    setup_logging(settings.log_level, settings.data_dir / "logs")

    ctx = AppContext(settings=settings)

    # Providers + routing.
    ctx.provider_registry = ProviderRegistry(settings)
    ctx.provider_registry.register_defaults()
    ctx.omni_router = OmniRouter(ctx.provider_registry, KeywordClassifier())
    ctx.fallback = FallbackChain(ctx.provider_registry)

    # Long-term memory (graph + extractor + retriever + decay).
    ctx.memory_graph = MemoryGraph.open(settings.graph_db_path)
    ctx.memory_retriever = MemoryRetriever(ctx.memory_graph)
    # placeholder-token-no-op
    ctx.fact_extractor = FactExtractor(ctx.memory_graph)

    # Short-term session + persistence.
    ctx.session = Session()
    ctx.session_store = SessionStore(settings.chat_db_path)
    restored = await ctx.session_store.load_latest(limit_messages=50)
    if restored:
        ctx.session = Session(session_id=restored["session_id"])
        for msg in restored["messages"]:
            ctx.session.add(msg["role"], msg["content"])

    # Personality + tools.
    ctx.personality = PersonalityLoader()
    ctx.tool_registry = ToolRegistry()
    ctx.tool_registry.register_defaults(data_dir=settings.data_dir, settings=settings)

    # Reply pipeline.
    context_builder = ContextBuilder(ctx.personality, ctx.session, ctx.memory_retriever)
    ctx.composer = ReplyComposer(
        router=ctx.omni_router,
        fallback=ctx.fallback,
        context_builder=context_builder,
        session=ctx.session,
        graph=ctx.memory_graph,
        extractor=ctx.fact_extractor,
        tools=ctx.tool_registry,
        extractor_queue=ctx.extractor_queue,
    )

    # Background tasks.
    ctx.spawn_background(ctx.fact_extractor.consume(ctx.extractor_queue, ctx.stop_event))
    ctx.spawn_background(decay_loop(ctx.memory_graph.store, ctx.stop_event))

    logger.info(
        "SACHA engine ready — providers=%s tools=%d facts=%d",
        ctx.provider_registry.configured_names(),
        len(ctx.tool_registry.describe_all()),
        ctx.memory_graph.stats()["facts"],
    )
    return ctx
