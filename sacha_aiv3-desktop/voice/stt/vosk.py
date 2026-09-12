"""
voice/stt/vosk.py — Vosk STT (fully offline, tiny models).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from voice.stt.base import STTError, STTProvider

logger = logging.getLogger(__name__)


class VoskSTT(STTProvider):
    name = "vosk"
    is_offline = True

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self._model = None

    def available(self) -> bool:
        if self.model_path is None:
            return False
        return (self.model_path / "conf").exists() or (self.model_path / "am").exists()

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from vosk import Model
        except ImportError as exc:  # pragma: no cover
            raise STTError("vosk is not installed") from exc
        if not self.available():
            raise STTError(f"vosk model not found at {self.model_path} (download one to data/models)")
        try:
            self._model = Model(str(self.model_path))
        except Exception as exc:
            raise STTError(f"failed to load vosk model: {exc}") from exc
        return self._model

    async def transcribe(
        self,
        audio_path: str | Path | None = None,
        audio_data: bytes | None = None,
        sample_rate: int = 16000,
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        model = self._load()

        async def _run() -> str:
            try:
                from vosk import KaldiRecognizer

                rec = KaldiRecognizer(model, sample_rate)
                chunks: list[bytes] = []
                if audio_path is not None:
                    path = Path(audio_path)
                    data = path.read_bytes()
                    chunks.append(data[44:] if data[:4] == b"RIFF" else data)  # strip wav header
                elif audio_data is not None:
                    chunks.append(audio_data)
                else:
                    raise STTError("no audio input given")

                parts: list[str] = []
                for chunk in chunks:
                    if rec.AcceptWaveform(chunk):
                        parts.append(json.loads(rec.Result()).get("text", ""))
                    else:
                        parts.append(json.loads(rec.PartialResult()).get("partial", ""))
                final = json.loads(rec.FinalResult()).get("text", "")
                if final:
                    parts.append(final)
                text = " ".join(p for p in parts if p).strip()
                if not text:
                    text = json.loads(rec.FinalResult()).get("text", "").strip()
                return text
            except STTError:
                raise
            except Exception as exc:
                raise STTError(f"vosk transcription failed: {exc}") from exc

        return await asyncio.to_thread(_run)
