"""Unit tests — core/reply/composer.py + context.py (reply pipeline)."""

import asyncio

import pytest

from core.reply.composer import ReplyComposer
from core.reply.context import ContextBuilder
from core.router.classifier import KeywordClassifier
from core.router.fallback import FallbackChain
from core.router.omni_router import OmniRouter


def test_reply_updates_session_and_returns_meta(composer):
    result = asyncio.run(composer.reply("hello there"))
    # 11 chars, no complexity markers → simple → local provider.
    assert result.provider == "local"
    assert result.text == "local reply"
    assert len(composer.session) == 2


def test_simple_greeting_routes_local(registry, session, personality):
    composer = ReplyComposer(
        router=OmniRouter(registry, KeywordClassifier()),
        fallback=FallbackChain(registry),
        context_builder=ContextBuilder(personality, session),
        session=session,
    )
    result = asyncio.run(composer.reply("hi"))
    assert result.provider == "local"


def test_stream_emits_tokens_then_done(composer):
    events = []

    async def go():
        async for event in composer.stream("hi"):
            events.append(event)

    asyncio.run(go())
    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "done" for e in events)
    assert len(composer.session) == 2


def test_stream_error_event_on_total_failure(settings, session, personality):
    from core.providers.registry import ProviderRegistry
    from core.router.classifier import KeywordClassifier
    from tests.conftest import FakeProvider

    reg = ProviderRegistry(settings)
    reg.register(FakeProvider(name="doomed", fail=True))
    composer = ReplyComposer(
        router=OmniRouter(reg, KeywordClassifier()),
        fallback=FallbackChain(reg),
        context_builder=ContextBuilder(personality, session),
        session=session,
    )
    events = []

    async def go():
        async for event in composer.stream("x"):
            events.append(event)

    asyncio.run(go())
    assert any(e["type"] == "error" for e in events)


def test_tool_short_circuit(composer_with_tools):
    result = asyncio.run(composer_with_tools.reply("!echo hello"))
    assert result.tool is not None
    assert "hello" in result.text


@pytest.fixture
def composer_with_tools(registry, session, personality, tmp_path):
    from core.tools.base import Tool
    from core.tools.registry import ToolRegistry

    tools = ToolRegistry()

    class EchoTool(Tool):
        name = "echo"
        description = "echoes input back"

        async def run(self, **kwargs):
            return kwargs.get("query", "")

    tools.register(EchoTool())
    return ReplyComposer(
        router=OmniRouter(registry, KeywordClassifier()),
        fallback=FallbackChain(registry),
        context_builder=ContextBuilder(personality, session),
        session=session,
        tools=tools,
    )


def test_context_builder_includes_system_and_history(composer, session):
    session.add("user", "first turn")
    session.add("assistant", "first reply")
    messages = composer.context_builder.build_messages("second turn", history_n=4)
    assert messages[0]["role"] == "system"
    assert any(m["content"] == "second turn" for m in messages)
    assert len(messages) == 4
