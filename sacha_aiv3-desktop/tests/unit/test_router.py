"""Unit tests — core/router/omni_router.py (provider selection)."""

from core.providers.base import ProviderError


def test_simple_chat_prefers_local(router):
    assert router.choose_provider("hello there") == "local"


def test_privacy_routes_to_local(router):
    assert router.choose_provider("my bank password is 1234") == "local"


def test_complex_routes_to_first_cloud(router, registry):
    assert registry.cloud_chain()[0] == "fake_cloud"
    assert router.choose_provider("explain the architecture and analyze the costs") == "fake_cloud"


def test_complete_returns_provider_name(router):
    import asyncio

    async def go():
        return await router.complete("hi", [{"role": "user", "content": "hi"}])

    text, provider = asyncio.run(go())
    assert text == "local reply"
    assert provider == "local"


def test_stream_returns_tokens_with_provider(router):
    import asyncio

    async def go():
        parts = []
        async for token, provider in router.stream("hi", [{"role": "user", "content": "hi"}]):
            parts.append((token, provider))
        return parts

    parts = asyncio.run(go())
    assert "".join(t for t, _ in parts) == "local reply"
    assert parts[0][1] == "local"


def test_unknown_provider_raises(router):
    import pytest


    with pytest.raises(ProviderError):
        router.registry.get("does_not_exist")


def test_describe_snapshot(router):
    snapshot = router.describe()
    assert "fake_cloud" in snapshot["configured_providers"]
    assert "cloud" in snapshot
    assert "local" in snapshot["cloud"] or "local" not in snapshot["cloud"]
