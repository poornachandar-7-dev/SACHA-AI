"""
vision/airdraw/clear_gesture.py — open-palm clear trigger.

An open palm (all five fingers extended) with a big enough bounding box
means "wipe the canvas". Kept as a pure predicate so reuse is trivial.
"""

from __future__ import annotations

from typing import Any

from vision.gesture.pipeline import classify_gesture


def is_open_palm(landmarks: list[Any], min_span: float = 0.3) -> bool:
    """True when the hand reads as an open palm occupying enough of the frame."""
    if len(landmarks) < 21:
        return False
    if classify_gesture(landmarks) != "open_palm":
        return False
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    span = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return max(span, height) >= min_span
