

"""
core/bootstrap.py — async event loop boot, wiring of all subsystems.
"""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass, field
from typing import Any

from core.config import Settings, get_settings
from core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@dataclass
class AppContext:
    """Holds every wired subsystem. Passed around instead of globals."""

    settings: Settings
    provider_registry: Any = None
    omni_router: Any = None
    memory_graph: Any = None
    fact_extractor: Any = None
    tool_registry: Any = None
    session_store: Any = None
    _background_tasks: set[asyncio.Task] = field(default_factory=set)

    def spawn_background(self, coro) -> asyncio.Task:
        """Track a background task so bootstrap can cancel it on shutdown."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def shutdown(self) -> None:
        logger.info("Shutting down: cancelling %d background task(s)", len(self._background_tasks))
        for task in list(self._background_tasks):
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

        "Will be coming in Future"
