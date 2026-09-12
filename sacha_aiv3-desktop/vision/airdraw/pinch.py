"""
vision/airdraw/pinch.py — thumb+index pinch trigger.

Pinch = the distance between thumb tip and index tip is small compared to
the whole-hand span. A controller handles JARVIS-style "pinch to draw"
transitions so callers keep clean state.
"""

from __future__ import annotations

import math
from typing import Any

_PINCH_THRESHOLD = 0.22
_PINCH_RELEASE = 0.32


def pinch_ratio(landmarks: list[Any]) -> float | None:
    """Normalized thumb→index distance. None if landmarks are unusable."""
    if len(landmarks) < 21:
        return None

    def pt(i: int) -> tuple[float, float]:
        return (landmarks[i].x, landmarks[i].y)

    thumb_tip, index_tip = pt(4), pt(8)
    pinky_base, index_mcp = pt(17), pt(5)
    scale = math.hypot(pinky_base[0] - index_mcp[0], pinky_base[1] - index_mcp[1]) or 1e-6
    return math.hypot(thumb_tip[0] - index_tip[0], thumb_tip[1] - index_tip[1]) / scale


class PinchController:
    """Pinch state machine with hysteresis (avoids flicker at the edge)."""

    def __init__(self) -> None:
        self._pinching = False

    def update(self, landmarks: list[Any]) -> bool:
        ratio = pinch_ratio(landmarks)
        if ratio is None:
            return self._pinching
        if self._pinching and ratio > _PINCH_RELEASE:
            self._pinching = False
        elif not self._pinching and ratio < _PINCH_THRESHOLD:
            self._pinching = True
        return self._pinching

    @property
    def pinching(self) -> bool:
        return self._pinching
