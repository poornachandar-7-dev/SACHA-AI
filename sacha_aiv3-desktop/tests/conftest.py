"""
tests/conftest.py — shared fixtures (tmp data, fake providers, graph, session).

Run from the project root with the runtime deps importable, e.g.:
    $env:PYTHONPATH="<project>;<project>\\.venv\\Lib\\site-packages"
    python -m pytest tests/unit -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Settings  # noqa: E402
from core.conversation.session import Session  # noqa: E402
from core.memory.graph import MemoryGraph  # noqa: E402
from core.providers.base import ModelProvider, ProviderError  # noqa: E402
from core.providers.registry import ProviderRegistry  # noqa: E402
from core.reply.composer import ReplyComposer  # noqa: E402
from core.reply.context import ContextBuilder  # noqa: E402
from core.router.classifier import KeywordClassifier  # noqa: E402
from core.router.fallback import FallbackChain  # noqa: E402
from core.router.omni_router import OmniRouter  # noqa: E402
from personality.loader import PersonalityLoader  # noqa: E402


class FakeProvider(ModelProvider):
    """Configurable fake provider for offline tests."""

    name = "fake"
    default_model = "fake-1"

    def __init__(
        self, reply: str = "fake response", fail: bool = False, delay: float = 0.0, name: str | None = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        if name:
            self.name = name
        self.reply = reply
        self.fail = fail
        self.delay = delay
        self.calls = 0

    @property
    def configured(self) -> bool:
        return True

    async def generate(self, messages, *, temperature=0.7, max_tokens=None, **kwargs) -> str:
        self.calls += 1
        import asyncio

        if self.fail:
            raise ProviderError(f"{self.name} exploded")
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.reply


class FakeCloudProvider(FakeProvider):
    name = "fake_cloud"
    is_local = False


class FakeLocalProvider(FakeProvider):
    name = "local"
    is_local = True


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path / "data", env="test", log_level="CRITICAL")


@pytest.fixture
def registry(settings) -> ProviderRegistry:
    reg = ProviderRegistry(settings)
    reg.register(FakeCloudProvider(reply="cloud reply"))
    reg.register(FakeLocalProvider(reply="local reply"))
    return reg


@pytest.fixture
def registry_with_failures(settings) -> ProviderRegistry:
    reg = ProviderRegistry(settings)
    reg.register(FakeCloudProvider(name="fake_cloud", fail=True))
    reg.register(FakeProvider(name="backup", reply="backup reply"))
    reg.register(FakeLocalProvider(reply="local reply"))
    return reg


@pytest.fixture
def graph(tmp_path) -> MemoryGraph:
    g = MemoryGraph.open(tmp_path / "graph.db")
    yield g
    g.close()


@pytest.fixture
def session() -> Session:
    return Session()


@pytest.fixture
def personality() -> PersonalityLoader:
    return PersonalityLoader()


@pytest.fixture
def router(registry) -> OmniRouter:
    return OmniRouter(registry, KeywordClassifier())


@pytest.fixture
def composer(registry, session) -> ReplyComposer:
    return ReplyComposer(
        router=OmniRouter(registry, KeywordClassifier()),
        fallback=FallbackChain(registry),
        context_builder=ContextBuilder(PersonalityLoader(), session),
        session=session,
    )


@pytest.fixture
def tool_registry(tmp_path):
    from core.tools.registry import ToolRegistry

    reg = ToolRegistry()
    reg.register_defaults(data_dir=tmp_path / "data")
    return reg
