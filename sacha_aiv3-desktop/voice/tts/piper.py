"""
voice/tts/piper.py — default offline TTS (Piper voices).

Piper synthesizes super-fast on CPU and gives a natural voice with the
``en_US-lessac-medium`` model. Model discovery: settings.piper_model_path, or
the standard Piper-onnx name inside ``data/models``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from voice.tts.base import TTSError, TTSProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "en_US-lessac-medium.onnx"


class PiperTTS(TTSProvider):
    name = "piper"
    is_offline = True

    def __init__(self, model_path: str | Path | None = None, models_dir: str | Path | None = None) -> None:
        self.models_dir = Path(models_dir) if models_dir else (Path.cwd() / "data" / "models")
        self.model_path = Path(model_path) if model_path else self.models_dir / _DEFAULT_MODEL
        self._voice = None

    def available(self) -> bool:
        return self.model_path.exists()

    def _load(self) -> Any:
        if self._voice is not None:
            return self._voice
        try:
            from piper import PiperVoice
        except ImportError as exc:  # pragma: no cover
            raise TTSError("piper-tts is not installed") from exc
        if not self.available():
            raise TTSError(
                f"piper model not found at {self.model_path} — download a .onnx voice into data/models"
            )
        try:
            self._voice = PiperVoice.load(str(self.model_path))
        except Exception as exc:
            raise TTSError(f"failed to load piper voice: {exc}") from exc
        return self._voice

    async def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        voice = self._load()
        target = Path(output_path) if output_path else self.models_dir.parent / "cache" / "audio" / "piper_out.wav"
        target.parent.mkdir(parents=True, exist_ok=True)

        def _sync() -> None:
            with open(target, "wb") as fh:
                voice.synthesize(text, fh)

        await asyncio.to_thread(_sync)
        return target
