"""
voice/barge_in.py — interrupt TTS mid-playback (V3 async requirement).

While SACHA is speaking, short prompts ("stop", "wait, actually…", the wake
word) should cancel playback immediately. This module watches the mic RMS
level; crossing a threshold while playback is active signals barge-in.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class BargeInDetector:
    """Samples the mic and reports whether speech is happening right now."""

    def __init__(self, threshold: float = 0.02, sample_rate: int = 16000, block_size: int = 1600, smoothing: float = 0.3) -> None:
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.smoothing = smoothing
        self._rms = 0.0

    def audio_available(self) -> bool:
        if sys.platform == "win32":
            return True
        try:
            import sounddevice  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def rms_of(samples: Any) -> float:
        import numpy as np

        arr = np.asarray(samples, dtype=np.float32)
        if arr.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(arr))))

    def is_speech(self, rms: float) -> bool:
        self._rms = self.smoothing * rms + (1 - self.smoothing) * self._rms
        return self._rms >= self.threshold


class BargeInManager:
    """Orchestrates interruption: enables/disables barge-in around TTS."""

    def __init__(self, detector: BargeInDetector | None = None, on_interrupt: Callable[[], Awaitable[None]] | None = None) -> None:
        self.detector = detector or BargeInDetector()
        self.on_interrupt = on_interrupt
        self.active = False
        self._task: asyncio.Task | None = None

    async def start(self, cancel_tts: Callable[[], Any]) -> None:
        """Begin monitoring the mic; call ``cancel_tts`` when speech detected."""
        if not self.detector.audio_available():
            logger.warning("barge-in unavailable: no audio device")
            return
        self.active = True
        self._task = asyncio.create_task(self._monitor(cancel_tts))

    async def stop(self) -> None:
        self.active = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _monitor(self, cancel_tts: Callable[[], Any]) -> None:
        import numpy as np
        import sounddevice as sd

        def _callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            if not self.active:
                return
            samples = indata[:, 0].astype(np.float32)
            if self.detector.is_speech(self.detector.rms_of(samples)):
                result = cancel_tts()
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
                self.active = False  # one-shot per activation

        with sd.InputStream(
            samplerate=self.detector.sample_rate,
            blocksize=self.detector.block_size,
            dtype="float32",
            channels=1,
            callback=_callback,
        ):
            while self.active:
                await asyncio.sleep(0.1)
