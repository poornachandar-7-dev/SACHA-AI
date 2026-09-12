"""
bridges/base.py — MessagingBridge interface.

Every platform bridge implements ``start/stop`` and pushes incoming messages
into a shared :class:`ConversationInbox` via ``dispatch``. The desktop HUD
and Telegram share the same underlying session so the assistant behaves
identically on both surfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class BridgeNotAvailable(RuntimeError):
    """Raised when a bridge lacks auth/tokens to start."""


@dataclass
class BridgeMessage:
    chat_id: str
    sender: str = "unknown"
    text: str = ""
    channel: str = "telegram"
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "sender": self.sender,
            "text": self.text,
            "channel": self.channel,
            "ts": self.ts,
        }


class MessagingBridge(ABC):
    """Contract + common plumbing for platform bridges."""

    name: str = "bridge"
    channel: str = "telegram"
    requires_auth: tuple[str, ...] = ()

    def __init__(self, inbox=None) -> None:
        # Lazy import keeps the base.py <-> session_share.py module graph acyclic.
        if inbox is None:
            from bridges.session_share import ConversationInbox

            inbox = ConversationInbox()
        self.inbox: Any = inbox
        self._auth: dict[str, Any] = {}

    # -- config --------------------------------------------------------------
    def configure(self, **auth: Any) -> None:
        missing = [k for k in self.requires_auth if not auth.get(k)]
        if missing:
            raise BridgeNotAvailable(f"{self.name} is missing: {', '.join(missing)}")
        self._auth.update(auth)

    @property
    def configured(self) -> bool:
        return all(self._auth.get(k) for k in self.requires_auth)

    def status(self) -> dict[str, Any]:
        return {"name": self.name, "channel": self.channel, "configured": self.configured}
    # -- lifecycle -------------------------------------------------------------
    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        pass

    # -- inbound routing ------------------------------------------------------------
    async def dispatch(self, message: BridgeMessage) -> bool:
        """Push an incoming platform message into the shared inbox."""
        return self.inbox.submit(message)
