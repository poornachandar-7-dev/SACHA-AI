"""
voice/wakeword/porcupine.py — Picovoice Porcupine wake-word engine.

Porcupine is the most accurate on-device engine but needs a free access key.
It is only marked available when a key is configured.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from voice.wakeword.base import WakeWordDetector, WakeWordError

logger = logging.getLogger(__name__)


class PorcupineDetector(WakeWordDetector):
    name = "porcupine"

    def __init__(
        self,
        phrase: str = "hey sacha",
        access_key: str | None = None,
        sample_rate: int = 16000,
        frame_length: int = 512,
        custom_model: str | Path | None = None,
    ) -> None:
        super().__init__(phrase=phrase)
        self.access_key = access_key
        self.sample_rate = sample_rate
        self.frame_length = frame_length
        self.custom_model = str(custom_model) if custom_model else None

    def available(self) -> bool:
        try:
            import pvporcupine  # noqa: F401
            import sounddevice  # noqa: F401
        except ImportError:
            return False
        return bool(self.access_key)

    async def detect(
        self,
        on_trigger: Callable[[], Awaitable[None]],
        stop_event: Any,
    ) -> None:
        if not self.available():
            raise WakeWordError(
                "Porcupine needs PV_ACCESS_KEY and an audio device — see docs/bridges or use openwakeword"
            )
        try:
            import pvporcupine
            import sounddevice as sd
        except ImportError as exc:  # pragma: no cover
            raise WakeWordError("pvporcupine not installed") from exc

        porcupine = pvporcupine.create(
            access_key=self.access_key,
            keyword_paths=[self.custom_model] if self.custom_model else None,
            keywords=["hey sacha"] if not self.custom_model else None,
        )

        async def _handler() -> None:
            result = on_trigger()
            if asyncio.iscoroutine(result):
                await result

        def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            pcm = indata[:, 0].tobytes()
            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                logger.info("wake word detected via porcupine")
                asyncio.run_coroutine_threadsafe(_handler(), asyncio.get_event_loop())

        try:
            with sd.InputStream(
                samplerate=porcupine.sample_rate,
                blocksize=porcupine.frame_length,
                channels=1,
                dtype="int16",
                callback=_callback,
            ):
                while not stop_event.is_set():
                    await asyncio.sleep(0.1)
        finally:
            porcupine.delete()
