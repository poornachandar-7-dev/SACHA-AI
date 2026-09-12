"""
vision/vlm/base.py — (planned) LLaVA / vision-language model interface.

The interface is stable now so the desktop HUD can request image captions;
a concrete VLM (local LLaVA via ollama, or a cloud vision model) plugs in
without touching the caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VLMError(RuntimeError):
    pass


class VLMProvider(ABC):
    """Contract for vision-language models."""

    name: str = "vlm"

    @abstractmethod
    async def caption(self, image_path: str | Path, prompt: str = "Describe this image briefly.") -> str:
        """Return a text caption for the image at ``image_path``."""
        raise NotImplementedError

    def available(self) -> bool:
        return False  # no concrete VLM until LLaVA/local wiring lands
