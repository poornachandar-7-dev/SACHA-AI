"""
vision/airdraw/canvas.py — persistent stroke buffer (V2 was redraw-per-frame).

Strokes accumulate here as (x, y) polylines; the HUD polls ``to_dict()``
each animation frame and paints them as an overlay. Storing the buffer
server-side means the drawing survives camera blips.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Stroke:
    points: list[tuple[float, float]] = field(default_factory=list)
    color: str = "#00e5ff"
    started_at: float = field(default_factory=time.time)

    def add(self, x: float, y: float) -> None:
        self.points.append((float(x), float(y)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "color": self.color,
            "started_at": self.started_at,
            "points": [[x, y] for x, y in self.points],
        }


class DrawCanvas:
    """Persistent in-memory stroke list with save/load."""

    def __init__(self, max_strokes: int = 200) -> None:
        self.strokes: list[Stroke] = []
        self.max_strokes = max_strokes
        self._current: Stroke | None = None

    def begin_stroke(self, x: float, y: float, color: str = "#00e5ff") -> None:
        self._current = Stroke(color=color)
        self._current.add(x, y)

    def extend_stroke(self, x: float, y: float) -> bool:
        """Add a point to the active stroke. Returns False if none is active."""
        if self._current is None:
            return False
        self._current.add(x, y)
        return True

    def end_stroke(self) -> Stroke | None:
        """Commit the active stroke and clear it."""
        stroke, self._current = self._current, None
        if stroke and stroke.points:
            self.strokes.append(stroke)
            if len(self.strokes) > self.max_strokes:
                self.strokes = self.strokes[-self.max_strokes :]
            return stroke
        return None

    def clear(self) -> None:
        self.strokes.clear()
        self._current = None

    @property
    def active(self) -> bool:
        return self._current is not None

    def to_dict(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.strokes]

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")
        return target

    def load(self, path: str | Path) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.strokes = [Stroke(points=[(p[0], p[1]) for p in s["points"]], color=s.get("color", "#00e5ff")) for s in raw]
