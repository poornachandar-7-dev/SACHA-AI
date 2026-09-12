"""
voice/stt — STT engine factory (default: faster-whisper, fully offline).
"""

from __future__ import annotations

from typing import Any

from voice.stt.base import STTError, STTProvider
from voice.stt.cloud_fallback import CloudFallbackSTT
from voice.stt.faster_whisper import FasterWhisperSTT
from voice.stt.vosk import VoskSTT


def get_stt_provider(engine: str = "faster_whisper", settings: Any | None = None) -> STTProvider:
    """Build an STT provider by name from settings (or defaults)."""
    settings = settings or {}
    if engine == "vosk":
        return VoskSTT(model_path=getattr(settings, "vosk_model_path", None) if settings else None)
    if engine == "whisper_cpp":
        raise STTError("whisper_cpp is not wired up yet — use faster_whisper or vosk")
    return FasterWhisperSTT(
        model_size=getattr(settings, "whisper_model_size", "base") if settings else "base",
        model_dir=getattr(settings, "models_dir", lambda: None)() if settings else None,
    )


def build_stt_chain(settings: Any | None = None) -> list[STTProvider]:
    """Local-first chain for the engine: [primary, cloud fallback if keyed]."""
    primary = get_stt_provider(
        getattr(settings, "stt_engine", "faster_whisper") if settings else "faster_whisper",
        settings,
    )
    chain = [primary]
    key = getattr(settings, "openai_api_key", None) if settings else None
    if key:
        chain.append(CloudFallbackSTT(api_key=key))
    return chain


__all__ = ["STTError", "STTProvider", "FasterWhisperSTT", "VoskSTT", "CloudFallbackSTT", "get_stt_provider", "build_stt_chain"]
