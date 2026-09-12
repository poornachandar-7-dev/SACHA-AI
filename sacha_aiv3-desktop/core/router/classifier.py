"""
core/router/classifier.py — intent + complexity classifier (keyword-based MVP).

Turns a free-text user message into a :class:`RoutingIntent` so the
OmniRouter can pick the cheapest provider that still answers well. This is a
deliberately cheap, deterministic MVP — it must classify in microseconds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Complexity = Literal["simple", "moderate", "complex"]

# Messages that never need a big model.
_SIMPLE_MARKERS = (
    "hi", "hello", "hey", "yo", "thanks", "thank you", "ok", "okay",
    "good morning", "good evening", "good night", "bye", "goodbye",
    "who are you", "what are you", "help", "status", "version",
)

# Emphasizes privacy; must never leave the machine.
_PRIVACY_MARKERS = (
    "password", "passwords", "secret", "credentials", "credit card",
    "bank", "medical", "health issue", "ssn", "social security",
    "private key", "vpn", "privacy", "confidential",
)

# High-complexity tasks where a cloud / bigger model usually wins.
_COMPLEX_MARKERS = (
    "explain", "analyze", "summar", "compare", "debug", "refactor",
    "architecture", "design ", "essay", "report", "translate",
    "interpret", "review", "optimize", "research", "write a",
)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "code": ("python", "javascript", "code", "function", "bug", "error log",
             "refactor", "debug", "syntax", "program"),
    "research": ("research", "latest", "news", "find", "search", "explain",
                 "compare", "how does", "why is", "what is the"),
    "math": ("calculate", "compute", "math", "sum of", "percentage", "equation"),
    "memory": ("remember", "what do you know about me", "who am i",
               "my name", "my birthday", "my favorite"),
    "reminder": ("remind me", "reminder", "schedule", "every morning",
                 "every day", "at 8", "at 9", "deadline"),
    "tool": ("open website", "search for", "weather", "screenshot",
             "clipboard", "volume up", "volume down", "mute", "start ",
             "run command", "set brightness", "open app"),
    "system": ("help", "status", "version", "what can you do", "who made you"),
}

# Explicit tool invocation syntax:  !toolname arg1 arg2
_TOOL_CALL_RE = re.compile(r"^!\s*([a-zA-Z_][\w-]*)\s*(.*)$", re.IGNORECASE)


@dataclass
class RoutingIntent:
    """Machine-readable verdict about how a message should be handled."""

    complexity: Complexity = "moderate"
    privacy_sensitive: bool = False
    category: str = "chat"
    provider_hint: str | None = None
    tool_hint: str | None = None
    matched_keywords: list[str] = field(default_factory=list)


class KeywordClassifier:
    """Deterministic keyword classifier used by the OmniRouter."""

    simple_markers: tuple[str, ...] = _SIMPLE_MARKERS
    privacy_markers: tuple[str, ...] = _PRIVACY_MARKERS
    complex_markers: tuple[str, ...] = _COMPLEX_MARKERS
    category_keywords: dict[str, tuple[str, ...]] = _CATEGORY_KEYWORDS

    def classify(
        self,
        text: str,
        available_tools: tuple[str, ...] = (),
    ) -> RoutingIntent:
        """Classify raw user text into a :class:`RoutingIntent`."""
        text = text.strip()
        lowered = text.lower()
        intent = RoutingIntent()
        intent.matched_keywords = self._hits(lowered, self.privacy_markers)

        # 1. Explicit tool calls always win.
        tool_call = _TOOL_CALL_RE.match(text)
        if tool_call and (not available_tools or tool_call.group(1) in available_tools):
            intent.category = "tool"
            intent.tool_hint = tool_call.group(1)
            intent.complexity = "simple"
            intent.provider_hint = "local"
            return intent

        # 2. Privacy trumps everything else.
        if intent.matched_keywords:
            intent.privacy_sensitive = True
            intent.complexity = "complex"
            intent.provider_hint = "local"
            intent.category = "private"
            return intent

        # 3. Category detection.
        for cat, keywords in self.category_keywords.items():
            hits = self._hits(lowered, keywords)
            if hits:
                intent.category = cat
                intent.matched_keywords = hits
                break

        # 4. Complexity.
        if len(text) > 400:
            intent.complexity = "complex"
        elif self._hits(lowered, self.complex_markers):
            intent.complexity = "complex"
        elif self._hits(lowered, self.simple_markers) or len(text) <= 40:
            intent.complexity = "simple"

        # 5. Provider hints per category.
        if intent.category == "reminder":
            intent.provider_hint = "local"
        elif intent.category in ("code", "research", "math"):
            intent.provider_hint = None  # router picks first available cloud
        return intent

    @staticmethod
    def _hits(text: str, markers: tuple[str, ...]) -> list[str]:
        return [m for m in markers if m in text]
