"""Unit tests — core/providers/base.py (the ModelProvider interface)."""

import asyncio

from core.providers.base import ModelProvider, ProviderError, normalize_messages


class EchoProvider(ModelProvider):
    name = "echo"
    default_model = "echo-1"

    async def generate(self, messages, *, temperature=0.7, max_tokens=None, **kwargs) -> str:
        return "echo: " + messages[-1]["content"]


def test_generate_roundtrip():
    provider = EchoProvider()
    assert asyncio.run(provider.generate([{"role": "user", "content": "ping"}])) == "echo: ping"


def test_default_stream_buffers_full_reply():
    provider = EchoProvider()

    async def go():
        parts = []
        async for token in provider.stream([{"role": "user", "content": "ping"}]):
            parts.append(token)
        return parts

    parts = asyncio.run(go())
    assert "".join(parts) == "echo: ping"


def test_configured_reflects_model():
    p = EchoProvider(model="x")
    assert p.configured is True
    assert p.supports("chat") is True
    assert p.supports("vision") is False


def test_normalize_messages():
    raw = [{"role": "user", "content": "a", "extra": 1}, {"role": "system", "content": "b"}]
    assert normalize_messages(raw) == [{"role": "user", "content": "a"}, {"role": "system", "content": "b"}]


def test_provider_error_is_runtime_error():
    assert issubclass(ProviderError, RuntimeError)


def test_provider_repr_and_display_name():
    p = EchoProvider()
    assert "echo" in repr(p)
    assert p.display_name
