"""
core/providers/base.py — abstract ModelProvider (the V3 interface).

Every model backend (NVIDIA NIM, OpenAI, Gemini, local Ollama) implements
this interface. The OmniRouter only ever talks to ModelProvider instances,
so swapping a provider never touches the reply pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

DEFAULT_CAPABILITIES = ("chat", "stream")


class ProviderError(RuntimeError):
    """Raised when a provider cannot produce a reply (auth, network, model)."""


class ModelProvider(ABC):
    """Contract implemented by every model backend."""

    name: str = "base"
    display_name: str = "Base provider"
    is_local: bool = False
    default_model: str = ""
    capabilities: tuple[str, ...] = DEFAULT_CAPABILITIES

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        self.model = model or self.default_model
        self._init_kwargs = kwargs

    # -- introspection ---------------------------------------------------
    @property
    def configured(self) -> bool:
        """True when this provider has everything it needs (keys, endpoint)."""
        return bool(self.model)

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    # -- call contract ----------------------------------------------------
    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Return the full assistant reply for an OpenAI-style message list."""

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Yield reply fragments as they arrive.

        Default implementation buffers the whole reply via ``generate`` and
        yields it once — providers that support true streaming override this.
        """
        yield await self.generate(
            messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        )

    async def close(self) -> None:
        """Release any resources (HTTP clients, loaded models)."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r} model={self.model!r} configured={self.configured}>"


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Coerce messages to the minimal ``{role, content}`` shape consumers expect."""
    return [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in messages
    ]
