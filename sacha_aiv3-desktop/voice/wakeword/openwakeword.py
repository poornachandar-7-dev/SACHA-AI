"""
voice/wakeword/openwakeword.py — OpenWakeWord local wake-word engine.

Uses the built-in community models when present; if a custom "hey SACHA"
model file exists in ``data/models`` under ``hey_sacha.onnx`` (optionally
with ``hey_sacha.json`` metadata), it is loaded with priority.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from importlib.resources import files
from pathlib import Path
from typing import Any

from voice.wakeword.base import WakeWordDetector, WakeWordError

logger = logging.getLogger(__name__)


class OpenWakeWordDetector(WakeWordDetector):
    name = "openwakeword"

    def __init__(
        self,
        phrase: str = "hey sacha",
        models_dir: str | Path | None = None,
        sample_rate: int = 16000,
        block_size: int = 1600,
        detection_threshold: float = 0.5,
    ) -> None:
        super().__init__(phrase=phrase)
        self.models_dir = Path(models_dir) if models_dir else (Path.cwd() / "data" / "models")
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.threshold = detection_threshold
        self._models: dict[str, Any] = {}

    def _model_names(self) -> list[str]:
        custom = self.models_dir / "hey_sacha.onnx"
        names: list[str] = []
        if custom.exists():
            names.append("hey_sacha")
        # Prefer our phrase match when possible; fall back to stock models.
        if self.phrase.lower() in ("hey sacha", "hey sasha", "hey saasha"):
            names.append("hey_jarvis" if not names else "")
        if not names:
            names = ["hey_jarvis", "alexa"]
        return [n for n in names if n]

    def available(self) -> bool:
        try:
            import openwakeword  # noqa: F401
            import sounddevice  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> Any:
        if self._models:
            return self._models
        try:
            from openwakeword.model import Model
        except ImportError as exc:  # pragma: no cover
            raise WakeWordError("openwakeword is not installed") from exc
        try:
            for name in self._model_names():
                local = self.models_dir / f"{name}.onnx"
                if local.exists():
                    self._models[name] = Model(wakeword_models={name: str(local)})
                else:
                    pkg_path = files("openwakeword").joinpath("models")  # pragma: no cover
                    self._models[name] = Model(wakeword_models={name: str(pkg_path / f"{name}.onnx")})
        except Exception as exc:
            raise WakeWordError(f"openwakeword model load failed: {exc}") from exc
        return self._models

    async def detect(
        self,
        on_trigger: Callable[[], Awaitable[None]],
        stop_event: Any,
    ) -> None:
        models = self._load()
        if not self.available():  # pragma: no cover
            raise WakeWordError("audio I/O unavailable for wake word")
        import numpy as np
        import sounddevice as sd

        def _audio_callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            audio = indata[:, 0].astype(np.float32)
            for model in models.values():
                pred = model.predict(audio)
                if max(pred.values(), default=0.0) >= self.threshold:
                    logger.info("wake word detected (%s)", self.phrase)
                    asyncio.run_coroutine_threadsafe(_trigger(), asyncio.get_event_loop())

        async def _trigger() -> None:
            result = on_trigger()
            if asyncio.iscoroutine(result):
                await result

        with sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="float32",
            channels=1,
            callback=_audio_callback,
        ):
            logger.info("listening for wake word %r (openwakeword)", self.phrase)
            while not stop_event.is_set():
                await asyncio.sleep(0.1)
