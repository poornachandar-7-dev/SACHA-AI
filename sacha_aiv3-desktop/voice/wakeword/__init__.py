"""
voice/wakeword — wake-word detector factory.
"""

from __future__ import annotations

from typing import Any

from voice.wakeword.base import WakeWordDetector, WakeWordError
from voice.wakeword.openwakeword import OpenWakeWordDetector
from voice.wakeword.porcupine import PorcupineDetector


def build_wakeword_chain(settings: Any | None = None) -> list[WakeWordDetector]:
    """Local engines in order of preference; the engine tries each in turn."""
    phrase = getattr(settings, "wakeword_phrase", "hey sacha") if settings else "hey sacha"
    models_dir = getattr(settings, "models_dir", lambda: None)() if settings else None
    chain: list[WakeWordDetector] = [OpenWakeWordDetector(phrase=phrase, models_dir=models_dir)]
    key = getattr(settings, "pvporcupine_access_key", None) if settings else None
    if key:
        chain.append(PorcupineDetector(phrase=phrase, access_key=key))
    return chain


__all__ = ["WakeWordDetector", "WakeWordError", "OpenWakeWordDetector", "PorcupineDetector", "build_wakeword_chain"]
