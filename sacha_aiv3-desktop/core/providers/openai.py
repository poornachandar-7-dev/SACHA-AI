"""
core/providers/openai.py — OpenAI-compatible chat provider (httpx).

Works against any OpenAI-compatible endpoint; NVIDIA NIM and many local
servers reuse the same API shape, so ``OpenAIProvider`` is subclassed by
``NvidiaProvider`` rather than re-implemented.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.providers.base import ModelProvider, ProviderError, normalize_messages


class OpenAIProvider(ModelProvider):
    name = "openai"
    display_name = "OpenAI"
    default_model = "gpt-4o-mini"
    base_url = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(model=model)
        self.api_key = api_key
        self.base_url = (base_url or self.base_url).rstrip("/")
        self.timeout = timeout
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.AsyncClient(headers=headers, timeout=self.timeout)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderError(f"{self.name}: missing API key (set env / .env)")
        return {"Authorization": f"Bearer {self.api_key}"}

    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        try:
            resp = await self._client.post(
                f"{self.base_url}/chat/completions", json=body, headers=self._headers()
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name} request failed: {exc}") from exc
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_messages(messages),
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=body,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield delta
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name} stream failed: {exc}") from exc

    async def close(self) -> None:
        await self._client.aclose()
