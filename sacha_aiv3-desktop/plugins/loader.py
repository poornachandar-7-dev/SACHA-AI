"""
plugins/loader.py — discovers + loads plugins from disk.

Plugin contract (each plugin directory):
- ``plugin.json`` — validated :class:`PluginManifest`
- ``plugin.py``   — module exposing at least ``run(action, payload, ctx)``

``ctx`` is a :class:`PluginContext` giving plugins access to the tool
registry + granted permissions + a logger.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from plugins.manifest import PluginManifest
from plugins.sandbox import PluginError, PluginSandbox

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "plugin.json"


@dataclass
class PluginContext:
    """Handed to every plugin invocation."""

    permissions: list[str] = field(default_factory=list)
    data_dir: str = "data"
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("plugin"))
    tool_registry: Any = None

    def can(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass
class PluginInfo:
    manifest: PluginManifest
    directory: Path
    module_name: str
    module: Any = None

    @property
    def name(self) -> str:
        return self.manifest.name

    def to_dict(self) -> dict[str, Any]:
        return self.manifest.to_dict() | {"directory": str(self.directory)}


class PluginLoader:
    """Discovers plugin dirs, loads them, and invokes with isolation."""

    def __init__(self, plugins_dir: str | Path | None = None, sandbox: PluginSandbox | None = None) -> None:
        self.plugins_dir = Path(plugins_dir) if plugins_dir else Path(__file__).resolve().parent / "examples"
        self.sandbox = sandbox or PluginSandbox()
        self._loaded: list[PluginInfo] = []

    # -- discovery ------------------------------------------------------------
    def discover(self) -> list[Path]:
        """All directories under plugins_dir that contain a plugin.json."""
        if not self.plugins_dir.exists():
            return []
        return sorted(p.parent for p in self.plugins_dir.rglob(MANIFEST_FILENAME))

    # -- loading ---------------------------------------------------------------
    def load(self, plugin_dir: str | Path, ctx: PluginContext | None = None) -> PluginInfo:
        directory = Path(plugin_dir)
        manifest = PluginManifest.load(directory / MANIFEST_FILENAME)
        module_path = directory / manifest.entry
        if not module_path.exists():
            raise FileNotFoundError(f"{manifest.name}: entry {module_path} missing")
        module_name = f"sacha_plugin_{manifest.name}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"{manifest.name}: cannot load {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        plugin = PluginInfo(manifest=manifest, directory=directory, module_name=module_name, module=module)
        self._loaded.append(plugin)

        _ctx = ctx or PluginContext(permissions=manifest.permissions)
        setup = getattr(module, "setup", None)
        if callable(setup):
            try:
                setup(_ctx)
            except Exception as exc:
                logger.warning("%s: setup() failed: %s", manifest.name, exc)
        return plugin

    def load_all(self, ctx: PluginContext | None = None) -> list[PluginInfo]:
        for directory in self.discover():
            try:
                self.load(directory, ctx=ctx)
                logger.info("loaded plugin %s", directory.name)
            except Exception as exc:
                logger.warning("skipping plugin %s: %s", directory.name, exc)
        return self._loaded

    # -- invocation ---------------------------------------------------------------
    async def invoke(
        self,
        plugin: PluginInfo,
        action: str = "run",
        payload: dict[str, Any] | None = None,
        ctx: PluginContext | None = None,
    ) -> Any:
        """Invoke ``run(action, payload, ctx)`` from the plugin module."""
        runner = getattr(plugin.module, "run", None)
        if not callable(runner):
            raise PluginError(f"{plugin.name}: module has no run()")
        _ctx = ctx or PluginContext(permissions=plugin.manifest.permissions)

        async def _wrapped():
            result = runner(action, payload or {}, _ctx)
            if asyncio.iscoroutine(result):
                return await result
            return result

        return await self.sandbox.call_async(_wrapped())

    def list_loaded(self) -> list[PluginInfo]:
        return list(self._loaded)
