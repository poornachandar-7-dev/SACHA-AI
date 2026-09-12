"""Unit tests — bridges (base + registry + session share)."""

import asyncio

import pytest

from bridges.base import BridgeMessage, BridgeNotAvailable, MessagingBridge
from bridges.registry import BridgeRegistry
from bridges.session_share import ConversationInbox


class FakeBridge(MessagingBridge):
    name = "fake"
    requires_auth = ("token",)
    started = False

    async def start(self) -> None:
        self.started = True


def test_configure_requires_auth():
    bridge = FakeBridge()
    with pytest.raises(BridgeNotAvailable):
        bridge.configure()
    bridge.configure(token="abc")
    assert bridge.configured is True


def test_unconfigured_bridge_is_reported():
    bridge = FakeBridge()
    status = bridge.status()
    assert status["configured"] is False


def test_bridge_message_to_dict():
    msg = BridgeMessage(chat_id="42", sender="bob", text="hi")
    d = msg.to_dict()
    assert d["chat_id"] == "42"
    assert d["text"] == "hi"
    assert d["ts"]


def test_conversation_inbox_roundtrip():
    inbox = ConversationInbox()
    msg = BridgeMessage(chat_id="7", text="hello")
    assert inbox.submit(msg) is True
    assert inbox.size == 1

    async def go():
        got = await inbox.get()
        assert got.text == "hello"
    asyncio.run(go())


def test_registry_reports_and_starts():
    reg = BridgeRegistry()
    reg.register(FakeBridge(), token="xyz")
    report = reg.status_report()
    assert report[0]["configured"] is True
    assert "fake" in reg.names()

    async def go():
        started = await reg.start_all()
        assert "fake" in started
        await reg.stop_all()

    asyncio.run(go())


def test_unknown_bridge_raises():
    reg = BridgeRegistry()
    with pytest.raises(KeyError):
        reg.get("telegram")
