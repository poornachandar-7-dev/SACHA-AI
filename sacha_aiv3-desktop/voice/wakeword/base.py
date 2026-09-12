"""
voice/wakeword/base.py — WakeWordDetector interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any


class WakeWordError(RuntimeError):
    """Raised when a wake-word engine cannot run on this machine."""


class WakeWordDetector(ABC):
    """Contract for wake-word engines."""

    name: str = "base_wakeword"
    phrase: str = ""

    def __init__(self, phrase: str = "hey sacha") -> None:
        self.phrase = phrase

    @abstractmethod
    def available(self) -> bool:
        """True when models + audio I/O exist for this engine."""
        raise NotImplementedError

    @abstractmethod
    async def detect(
        self,
        on_trigger: Callable[[], Awaitable[None]] | Callable[[], None],
        stop_event: Any,
    ) -> None:
        """Continuously listen; call ``on_trigger`` when the phrase is heard."""
        raise NotImplementedError
