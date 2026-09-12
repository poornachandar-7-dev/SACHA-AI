"""
voice/stt/cloud_fallback.py — cloud STT used only when local fails.

Wraps the OpenAI transcriptions endpoint (whisper-1). Only constructed when
an OpenAI/cloud key exists; the engine layer decides whether local failed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from voice.stt.base import STTError, STTProvider

logger = logging.getLogger(__name__)


class CloudFallbackSTT(STTProvider):
    name = "cloud_fallback"
    is_offline = False

    def __init__(self, api_key: str | None = None, client_class: Any = None) -> None:
        self.api_key = api_key
        self._client_class = client_class  # injectable for tests

    def available(self) -> bool:
        return bool(self.api_key)

    async def transcribe(
        self,
        audio_path: str | Path | None = None,
        audio_data: bytes | None = None,
        sample_rate: int = 16000,
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        if not self.api_key:
            raise STTError("cloud STT requires an API key")
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover
            raise STTError("openai package not installed") from exc

        client = self._client_class(api_key=self.api_key) if self._client_class else AsyncOpenAI(api_key=self.api_key)

        async def _run() -> str:
            try:
                if audio_path is not None:
                    with open(audio_path, "rb") as fh:
                        result = await client.audio.transcriptions.create(model=kwargs.get("model", "whisper-1"), file=fh)
                        return result.text or ""
                raise STTError("cloud STT requires an audio file path")
            except Exception as exc:
                raise STTError(f"cloud STT failed: {exc}") from exc

        return await _run()
