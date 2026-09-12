"""Unit tests — core/router/fallback.py."""

import asyncio

import pytest

from core.providers.base import ProviderError
from core.router.fallback import FallbackChain


def test_order_prefers_cloud_then_local(registry):
    chain = FallbackChain(registry)
    order = chain.order(preferred="fake_cloud")
    assert order[0] == "fake_cloud"
    assert order[-1] == "local"


def test_complete_falls_back_to_backup(registry_with_failures):
    chain = FallbackChain(registry_with_failures)

    async def go():
        return await chain.complete("fake_cloud", [{"role": "user", "content": "hi"}])

    text, provider = asyncio.run(go())
    assert provider == "backup"
    assert text == "backup reply"


def test_complete_raises_when_all_fail(settings):
    from core.providers.registry import ProviderRegistry
    from tests.conftest import FakeProvider

    reg = ProviderRegistry(settings)
    reg.register(FakeProvider(name="a", fail=True))
    reg.register(FakeProvider(name="b", fail=True))
    chain = FallbackChain(reg)

    with pytest.raises(ProviderError):
        asyncio.run(chain.complete(None, [{"role": "user", "content": "hi"}]))


def test_stream_falls_back_before_first_token(registry_with_failures):
    chain = FallbackChain(registry_with_failures)

    async def go():
        parts = []
        async for token, provider in chain.stream("fake_cloud", [{"role": "user", "content": "hi"}]):
            parts.append((token, provider))
        return parts

    parts = asyncio.run(go())
    assert "".join(t for t, _ in parts) == "backup reply"
    assert parts[0][1] == "backup"


def test_stream_propagates_mid_stream_failure(settings):
    from core.providers.base import ProviderError
    from core.providers.registry import ProviderRegistry
    from tests.conftest import FakeProvider

    class MidFail(FakeProvider):

        async def stream(self, messages, **kw):
            yield "partial "
            raise ProviderError("mid-stream failure")

    reg = ProviderRegistry(settings)
    reg.register(MidFail(name="mid"))
    chain = FallbackChain(reg)

    with pytest.raises(ProviderError):
        asyncio.run(_drain(chain.stream("mid", [{"role": "user", "content": "x"}])))


async def _drain(agen):
    async for _ in agen:
        pass
