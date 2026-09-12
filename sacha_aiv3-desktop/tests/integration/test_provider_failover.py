"""
tests/integration/test_provider_failover.py — offline provider failover.

Uses the real FallbackChain + registry wiring with a cloud provider that
explodes and a local provider that answers. No network needed.
"""

from __future__ import annotations

import asyncio

from core.providers.registry import ProviderRegistry
from core.router.fallback import FallbackChain
from tests.conftest import FakeCloudProvider, FakeLocalProvider


def test_cloud_failure_falls_back_to_local(settings):
    reg = ProviderRegistry(settings)
    reg.register(FakeCloudProvider(name="nvidia", fail=True))
    reg.register(FakeLocalProvider(reply="offline answer"))
    chain = FallbackChain(reg)

    text, provider = asyncio.run(chain.complete("nvidia", [{"role": "user", "content": "hi"}]))
    assert text == "offline answer"
    assert provider == "local"


def test_stream_fall_back_before_tokens(settings):
    reg = ProviderRegistry(settings)
    reg.register(FakeCloudProvider(name="openai", fail=True))
    reg.register(FakeLocalProvider(reply="still here"))
    chain = FallbackChain(reg)

    async def go():
        tokens = []
        async for token, provider in chain.stream("openai", [{"role": "user", "content": "hi"}]):
            tokens.append((token, provider))
        return tokens

    tokens = asyncio.run(go())
    assert "".join(t for t, _ in tokens) == "still here"
