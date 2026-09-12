"""
voice/stt/faster_whisper.py — default offline STT (CTranslate2 Whisper).

The model is loaded lazily on first use and kept in process. Because the
CTranslate2 call is synchronous and CPU-bound, it runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from voice.stt.base import STTError, STTProvider

logger = logging.getLogger(__name__)


class FasterWhisperSTT(STTProvider):
    name = "faster_whisper"
    is_offline = True

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        model_dir: str | Path | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model_dir = Path(model_dir) if model_dir else None
        self._model = None  # lazy; downloading happens on first transcribe

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover
            raise STTError("faster-whisper is not installed") from exc
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(self.model_dir) if self.model_dir else None,
            )
            logger.info("faster-whisper model %r loaded", self.model_size)
        except Exception as exc:
            raise STTError(f"failed to load whisper model {self.model_size}: {exc}") from exc
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
                if audio_path is not None:
                    segments, _info = model.transcribe(
                        str(audio_path),
                        beam_size=kwargs.get("beam_size", 5),
                        vad_filter=kwargs.get("vad_filter", True),
                        language=language,
                    )
                elif audio_data is not None:
                    # faster-whisper accepts raw PCM when given sample rate.
                    import numpy as np

                    pcm = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    segments, _info = model.transcribe(
                        pcm,
                        beam_size=kwargs.get("beam_size", 5),
                        vad_filter=kwargs.get("vad_filter", True),
                        language=language,
                    )
                else:
                    raise STTError("no audio input given")
                return " ".join(seg.text.strip() for seg in segments).strip()
            except STTError:
                raise
            except Exception as exc:
                raise STTError(f"whisper transcription failed: {exc}") from exc

        return await asyncio.to_thread(_run)
