"""
bridges/registry.py — active bridges + auth state.

Holds every registered MessagingBridge, tracks which are configured, and
reports the status the HUD gateway screen renders.
"""

from __future__ import annotations

from typing import Any

from bridges.base import MessagingBridge
from bridges.session_share import ConversationInbox


class BridgeRegistry:
    """Registry of bridge instances + auth state."""

    def __init__(self) -> None:
        self._bridges: dict[str, MessagingBridge] = {}
        self.inbox = ConversationInbox()

    def register(self, bridge: MessagingBridge, **auth: Any) -> MessagingBridge:
        if auth:
            bridge.configure(**auth)
        self._bridges[bridge.name] = bridge
        return bridge

    def get(self, name: str) -> MessagingBridge:
        try:
            return self._bridges[name]
        except KeyError:
            raise KeyError(f"unknown bridge {name!r} (registered: {', '.join(self.names())})") from None

    def has(self, name: str) -> bool:
        return name in self._bridges

    def names(self) -> list[str]:
        return list(self._bridges)

    def configured(self) -> list[MessagingBridge]:
        return [b for b in self._bridges.values() if b.configured]

    def status_report(self) -> list[dict[str, Any]]:
        return [b.status() for b in self._bridges.values()]

    async def start_all(self) -> list[str]:
        started: list[str] = []
        for bridge in self.configured():
            try:
                await bridge.start()
                started.append(bridge.name)
            except Exception as exc:
                print(f"[bridge] {bridge.name} failed to start: {exc}")
        return started

    async def stop_all(self) -> None:
        for bridge in self._bridges.values():
            try:
                await bridge.stop()
            except Exception:
                pass
