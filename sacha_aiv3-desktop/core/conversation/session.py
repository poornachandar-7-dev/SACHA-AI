"""
core/conversation/session.py — short-term in-session history (V3 con fix).

The session is an in-memory ring buffer of the current conversation. The
full history is never resent to a provider; only the recent window plus a
memory subgraph (see core.reply.context) enters the prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: str = field(default_factory=_now)
    id: int | None = None  # assigned once persisted


class Session:
    """In-memory conversation state with a capped history window."""

    def __init__(self, session_id: str | None = None, max_history: int = 100) -> None:
        self.session_id = session_id or _now().replace(":", "").replace("-", "")
        self.max_history = max_history
        self._messages: list[Message] = []

    def add(self, role: str, content: str) -> Message:
        msg = Message(role=role, content=content)
        self._messages.append(msg)
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history :]
        return msg

    def messages(self) -> list[Message]:
        return list(self._messages)

    def last_n(self, n: int | None = None) -> list[Message]:
        if n is None:
            return list(self._messages)
        return self._messages[-n:]

    def as_dicts(self, n: int | None = None) -> list[dict[str, str]]:
        """OpenAI-style ``[{role, content}]`` list for provider calls."""
        return [{"role": m.role, "content": m.content} for m in self.last_n(n)]

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session {self.session_id[:8]} msgs={len(self._messages)}>"

    @property
    def last_user_text(self) -> str:
        for m in reversed(self._messages):
            if m.role == "user":
                return m.content
        return ""

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "message_count": len(self._messages),
            "last_user_text": self.last_user_text,
        }
