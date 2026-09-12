"""
voice/tts/sapi_fallback.py — Windows SAPI last-resort TTS.

Drives the built-in SAPI voice through PowerShell (System.Speech), so this
works with zero extra downloads on any Windows machine. Used only when Piper
(or another primary engine) is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

from voice.tts.base import TTSError, TTSProvider

logger = logging.getLogger(__name__)

_PS_SYNTH = """
$out = '{output}'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile($out)
$synth.Speak([Console]::In.ReadToEnd())
$synth.Dispose()
"""


class SapiFallbackTTS(TTSProvider):
    name = "sapi"
    is_offline = True

    async def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        target = Path(output_path) if output_path else Path.cwd() / "data" / "cache" / "audio" / "sapi_out.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        ps = _PS_SYNTH.replace("{output}", str(target))
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", ps,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        await proc.communicate(input=text.encode("utf-8"))
        if not target.exists():
            raise TTSError("SAPI synthesis produced no output file")
        return target
