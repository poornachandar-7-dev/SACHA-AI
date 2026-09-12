"""
vision/gesture/pipeline.py — MediaPipe hand tracking -> scene events.

Wraps MediaPipe Hands behind a simple ``process(BGR frame) -> events`` API
so the HUD layer never touches MediaPipe directly. Gestures: open palm,
fist, pinch, point, (two-hand) both open.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HandLandmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


@dataclass
class GestureEvent:
    hand: str  # "left" | "right"
    gesture: str  # "open_palm" | "fist" | "pinch" | "point" | "none"
    landmarks: list[HandLandmark] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hand": self.hand,
            "gesture": self.gesture,
            "confidence": round(self.confidence, 3),
            "landmarks": [
                {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in self.landmarks
            ],
        }


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def classify_gesture(landmarks: list[HandLandmark], threshold: float = 0.06) -> str:
    """Classify one hand's landmarks into a gesture name."""
    if len(landmarks) < 21:
        return "none"
    tips = [4, 8, 12, 16, 20]
    base = [3, 6, 10, 14, 18]
    wrist = (landmarks[0].x, landmarks[0].y)

    def extended(finger: int) -> bool:
        tip = (landmarks[tips[finger]].x, landmarks[tips[finger]].y)
        pip = (landmarks[base[finger]].x, landmarks[base[finger]].y)
        return _distance(tip, wrist) > _distance(pip, wrist) + threshold

    ext = [extended(i) for i in range(1, 5)]  # index, middle, ring, pinky

    # Pinch: thumb tip close to index tip.
    thumb_tip = (landmarks[4].x, landmarks[4].y)
    index_tip = (landmarks[8].x, landmarks[8].y)
    if _distance(thumb_tip, index_tip) < threshold * 1.5 and not ext[0]:
        return "pinch"

    if all(ext):
        return "open_palm"
    if not any(ext):
        return "fist"
    if ext[0] and not any(ext[1:]):
        return "point"
    return "none"


class GesturePipeline:
    """MediaPipe Hands wrapper (lazy init so import stays lightweight)."""

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._hands = None

    def available(self) -> bool:
        try:
            import cv2  # noqa: F401
            import mediapipe  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure_loaded(self) -> Any:
        if self._hands is not None:
            return self._hands
        try:
            from mediapipe.python.solutions import hands
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("mediapipe is not installed") from exc
        self._hands = hands.Hands(
            static_image_mode=False,
            max_num_hands=self.max_num_hands,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        return self._hands

    def process(self, frame_bgr: Any) -> list[GestureEvent]:
        """Detect hands in one BGR frame; return gesture events."""
        hands = self._ensure_loaded()
        import cv2

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)
        events: list[GestureEvent] = []
        if not result.multi_hand_landmarks:
            return events
        for hand_lms, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
            label = (handedness.classification[0].label or "Right").lower()
            side = "left" if label.startswith("left") else "right"
            lms = [HandLandmark(lm.x, lm.y, lm.z, lm.visibility) for lm in hand_lms.landmark]
            events.append(
                GestureEvent(
                    hand=side,
                    gesture=classify_gesture(lms),
                    landmarks=lms,
                    confidence=handedness.classification[0].score or 0.0,
                )
            )
        # Swap sides because the camera mirrors the output (Webcam convention).
        for event in events:
            event.hand = "right" if event.hand == "left" else "left"
        return events

    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()
            self._hands = None
