"""
core/providers/gemini.py — Google Gemini provider (httpx REST).

Uses the generativelanguage REST API directly (no SDK dependency) so the
streaming path stays consistent with the other providers. System messages
are folded into Gemini's ``systemInstruction`` field.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.providers.base import ModelProvider, ProviderError, normalize_messages


class GeminiProvider(ModelProvider):
    name = "gemini"
    display_name = "Google Gemini"
    default_model = "gemini-2.5-flash"
    api_base = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(model=model)
        self.api_key = api_key
        self.timeout = timeout
        self._client = client or httpx.AsyncClient(timeout=self.timeout)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    # -- helpers ----------------------------------------------------------
    def _url(self, endpoint: str) -> str:
        return f"{self.api_base}/models/{self.model}:{endpoint}?key={self.api_key}"

    @staticmethod
    def _to_gemini(messages: list[dict[str, Any]]) -> tuple[str | None, list[dict]]:
        """Split out a system message; convert roles to user/model."""
        system = None
        contents: list[dict[str, Any]] = []
        for m in normalize_messages(messages):
            role = m["role"]
            if role == "system":
                system = (system + "\n" if system else "") + m["content"]
                continue
            contents.append(
                {
                    "role": "model" if role in ("assistant", "model") else "user",
                    "parts": [{"text": m["content"]}],
                }
            )
        if not contents:  # Gemini requires at least one content turn
            contents.append({"role": "user", "parts": [{"text": ""}]})
        return system, contents

    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        if not self.api_key:
            raise ProviderError("gemini: missing API key (set GEMINI_API_KEY)")
        system, contents = self._to_gemini(messages)
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if max_tokens:
            body["generationConfig"]["maxOutputTokens"] = max_tokens
        try:
            resp = await self._client.post(self._url("generateContent"), json=body)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"gemini request failed: {exc}") from exc
        return self._extract_text(resp.json())

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise ProviderError("gemini: missing API key (set GEMINI_API_KEY)")
        system, contents = self._to_gemini(messages)
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if max_tokens:
            body["generationConfig"]["maxOutputTokens"] = max_tokens
        try:
            async with self._client.stream(
                self._url("streamGenerateContent") + "&alt=sse", json=body
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw)
                    except ValueError:
                        continue
                    text = self._extract_text(chunk)
                    if text:
                        yield text
        except httpx.HTTPError as exc:
            raise ProviderError(f"gemini stream failed: {exc}") from exc

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        parts: list[str] = []
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    parts.append(part["text"])
                elif "thought" in part and part.get("thought"):
                    parts.append(part["thought"])
        return "".join(parts)

    async def close(self) -> None:
        await self._client.aclose()
