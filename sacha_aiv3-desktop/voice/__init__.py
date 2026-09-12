"""
voice — fully offline voice pipeline (STT / TTS / wake word / barge-in).
"""

__version__ = "0.1.0"

from voice.barge_in import BargeInDetector, BargeInManager
from voice.stt.base import STTError, STTProvider
from voice.tts.base import TTSError, TTSProvider
from voice.wakeword.base import WakeWordDetector, WakeWordError

__all__ = [
    "__version__",
    "BargeInDetector",
    "BargeInManager",
    "STTError",
    "STTProvider",
    "TTSError",
    "TTSProvider",
    "WakeWordError",
    "WakeWordDetector",
]
