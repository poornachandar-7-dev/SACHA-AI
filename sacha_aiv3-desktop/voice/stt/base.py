"""
voice/stt/base.py — STTProvider interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class STTError(RuntimeError):
    """Raised when speech-to-text fails or no engine is available."""


class STTProvider(ABC):
    """Contract for speech-to-text backends."""

    name: str = "base_stt"
    is_offline: bool = True

    @abstractmethod
    async def transcribe(
        self,
        audio_path: str | Path | None = None,
        audio_data: bytes | None = None,
        sample_rate: int = 16000,
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Transcribe audio (from a file or raw bytes) to text."""
        raise NotImplementedError

    def available(self) -> bool:
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.name!r} offline={self.is_offline}>"
