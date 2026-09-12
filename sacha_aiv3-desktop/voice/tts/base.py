"""
voice/tts/base.py — TTSProvider interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSError(RuntimeError):
    """Raised when text-to-speech fails."""


class TTSProvider(ABC):
    """Contract for text-to-speech backends."""

    name: str = "base_tts"
    is_offline: bool = True

    @abstractmethod
    async def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        """Render text to a WAV file and return its path."""
        raise NotImplementedError

    async def speak(self, text: str) -> None:
        """Synthesize + play through the default audio output."""
        wav = await self.synthesize(text)
        await self.play(wav)

    async def play(self, wav_path: str | Path) -> None:
        """Play a WAV file (async via a worker thread)."""
        import asyncio
        import sys

        path = Path(wav_path)
        if sys.platform == "win32":
            import winsound

            await asyncio.to_thread(winsound.PlaySound, str(path), winsound.SND_FILENAME)
        else:
            import subprocess

            await asyncio.to_thread(subprocess.call, ["aplay", str(path)])

    async def stop(self) -> None:
        """Interrupt any in-flight playback (subclass overrides)."""

    def available(self) -> bool:
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.name!r} offline={self.is_offline}>"
