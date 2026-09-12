"""
plugins/manifest.py — manifest schema (name, perms, version).

Every plugin ships a ``plugin.json`` describing itself. The loader validates
it against this pydantic model before touching the plugin code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from plugins.permissions import known_permission


class PluginManifest(BaseModel):
    """plugin.json schema."""

    name: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    version: str = "0.1.0"
    author: str = "anonymous"
    description: str = ""
    entry: str = "plugin.py"
    permissions: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("permissions")
    @classmethod
    def _check_permissions(cls, value: list[str]) -> list[str]:
        unknown = [p for p in value if not known_permission(p)]
        if unknown:
            raise ValueError(f"unknown permissions in plugin.json: {', '.join(unknown)}")
        return value

    def perm_set(self) -> set[str]:
        """Granted permissions as a set (fast membership checks)."""
        return set(self.permissions)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def load(cls, path: str | Path) -> PluginManifest:
        """Load + validate a plugin.json file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**raw)
