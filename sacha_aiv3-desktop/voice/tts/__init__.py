"""
voice/tts — TTS engine factory (default: piper, fully offline).
"""

from __future__ import annotations

from typing import Any

from voice.tts.base import TTSError, TTSProvider
from voice.tts.piper import PiperTTS
from voice.tts.sapi_fallback import SapiFallbackTTS


def get_tts_provider(engine: str = "piper", settings: Any | None = None) -> TTSProvider:
    """Build a TTS provider by name (piper default; sapi is the fallback)."""
    if engine not in ("piper", "kokoro", "coqui", "sapi"):
        engine = "piper"
    if engine == "sapi":
        return SapiFallbackTTS()
    return PiperTTS(
        model_path=getattr(settings, "piper_model_path", None) if settings else None,
        models_dir=getattr(settings, "models_dir", lambda: None)() if settings else None,
    )


def build_tts_chain(settings: Any | None = None) -> list[TTSProvider]:
    """Primary engine first, Windows SAPI as the guaranteed last resort."""
    primary = get_tts_provider(
        getattr(settings, "tts_engine", "piper") if settings else "piper",
        settings,
    )
    return [primary, SapiFallbackTTS()]


__all__ = ["TTSError", "TTSProvider", "PiperTTS", "SapiFallbackTTS", "get_tts_provider", "build_tts_chain"]
