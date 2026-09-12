"""
personality/loader.py — loads SOUL.md into every AI call.

The loader owns the "active personality": it reads ``SOUL.md``, applies a
preset on request (backups the previous SOUL.md into ``history/`` so the
user can revert), and snapshots the file on every HUD save.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONALITY_DIR = Path(__file__).resolve().parent
DEFAULT_SOUL = PERSONALITY_DIR / "SOUL.md"
PRESETS_DIR = PERSONALITY_DIR / "presets"
HISTORY_DIR = PERSONALITY_DIR / "history"


class PersonalityError(RuntimeError):
    pass


class PersonalityLoader:
    """Active personality accessor + preset manager."""

    def __init__(
        self,
        soul_path: str | Path | None = None,
        presets_dir: str | Path | None = None,
        history_dir: str | Path | None = None,
    ) -> None:
        self.soul_path = Path(soul_path) if soul_path else DEFAULT_SOUL
        self.presets_dir = Path(presets_dir) if presets_dir else PRESETS_DIR
        self.history_dir = Path(history_dir) if history_dir else HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def system_prompt(self) -> str:
        """The SOUL instructions pasted into the system message."""
        if not self.soul_path.exists():
            raise PersonalityError(f"SOUL.md not found at {self.soul_path}")
        return self.soul_path.read_text(encoding="utf-8").strip()

    def identity(self) -> dict[str, str]:
        """Name + creators (HUD display)."""

        return {"name": "SACHA", "origin": "original identity — not a JARVIS clone"}

    # -- presets ------------------------------------------------------------
    def list_presets(self) -> list[str]:
        if not self.presets_dir.exists():
            return []
        return sorted(p.stem for p in self.presets_dir.glob("*.md"))

    def load_preset(self, name: str) -> str:
        path = self.presets_dir / f"{name}.md"
        if not path.exists():
            raise PersonalityError(f"unknown preset {name!r} (available: {', '.join(self.list_presets())})")
        return path.read_text(encoding="utf-8").strip()

    def apply_preset(self, name: str) -> Path:
        """Backup current SOUL.md, then replace it with the preset content."""
        if name in ("default", "current") and name == "default":
            content = self.load_preset("default")
        else:
            content = self.load_preset(name)
        saved = self.save_snapshot()
        self.soul_path.write_text(content + "\n", encoding="utf-8")
        return saved

    # -- history -------------------------------------------------------------
    def save_snapshot(self) -> Path:
        """Copy current SOUL.md into history/ with a timestamped filename."""
        if not self.soul_path.exists():
            raise PersonalityError("nothing to snapshot — SOUL.md missing")
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
        target = self.history_dir / f"{stamp}.md"
        shutil.copyfile(self.soul_path, target)
        return target

    def list_snapshots(self) -> list[Path]:
        return sorted(self.history_dir.glob("*.md"), reverse=True)
