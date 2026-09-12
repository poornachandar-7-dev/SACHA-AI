"""
core/providers/local.py — Ollama / llama.cpp local provider.

Talks to the Ollama HTTP API (default http://localhost:11434). Supports both
full replies and token streaming via NDJSON. Used for privacy-sensitive work
and as the universal fallback when every cloud provider fails.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.providers.base import ModelProvider, ProviderError, normalize_messages


class LocalProvider(ModelProvider):
    name = "local"
    display_name = "Local (Ollama)"
    is_local = True
    default_model = "llama3"

    def __init__(
        self,
        model: str | None = None,
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(model=model)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client or httpx.AsyncClient(timeout=self.timeout)

    @property
    def configured(self) -> bool:
        return True  # local is always available to try

    def _chat_url(self) -> str:
        return f"{self.base_url}/api/chat"

    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        payload = self._payload(messages, temperature=temperature, stream=False)
        if max_tokens:
            payload["options"] = {**(payload.get("options") or {}), "num_predict": max_tokens}
        try:
            resp = await self._client.post(self._chat_url(), json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"local Ollama request failed: {exc}") from exc
        data = resp.json()
        return data.get("message", {}).get("content", "") or ""

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature=temperature, stream=True)
        try:
            async with self._client.stream("POST", self._chat_url(), json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except ValueError:
                        continue
                    delta = data.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if data.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise ProviderError(f"local Ollama stream failed: {exc}") from exc

    def _payload(self, messages, *, temperature, stream) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": normalize_messages(messages),
            "stream": stream,
            "options": {"temperature": temperature},
        }

    async def models(self) -> list[str]:
        """List model names available on the Ollama server (info helper)."""
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
        except httpx.HTTPError:
            return []
        return sorted(m["name"] for m in resp.json().get("models", []))

    async def healthcheck(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=3.0)
            return resp.status_code < 400
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
