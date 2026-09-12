"""Unit tests — plugins (manifest, permissions, loader, sandbox)."""

import asyncio
import json

import pytest

from plugins.manifest import PluginManifest
from plugins.permissions import Permission, known_permission
from plugins.sandbox import PluginError, PluginSandbox


@pytest.fixture
def plugin_dir(tmp_path):
    d = tmp_path / "demo"
    d.mkdir()
    (d / "plugin.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "version": "1.0.0",
                "author": "test",
                "description": "demo plugin",
                "permissions": ["network"],
            }
        ),
        encoding="utf-8",
    )
    (d / "plugin.py").write_text(
        "from plugins.loader import PluginContext\n"
        "def setup(ctx: PluginContext): ctx.logger.info('setup ran')\n"
        "def run(action, payload, ctx):\n"
        "    if action == 'help': return 'demo help'\n"
        "    return 'ran: ' + payload.get('x', '') + ' can_net=' + str(ctx.can('network'))\n",
        encoding="utf-8",
    )
    return d


def test_manifest_valid_permissions():
    m = PluginManifest(name="ok", permissions=["network", "fs"])
    assert m.perm_set() == {"network", "fs"}


def test_manifest_rejects_unknown_permission():
    with pytest.raises(ValueError):
        PluginManifest(name="bad", permissions=["root_of_all_evil"])


def test_permissions_enum_and_lookup():
    assert Permission.FS.value == "fs"
    assert known_permission("exec") is True
    assert known_permission("bogus") is False


def test_loader_discovers_and_runs(plugin_dir, tmp_path):
    from plugins.loader import PluginContext, PluginLoader

    loader = PluginLoader(plugins_dir=plugin_dir.parent)
    infos = loader.load_all(ctx=PluginContext(permissions=["network"], data_dir=str(tmp_path)))
    assert len(infos) == 1
    assert infos[0].name == "demo"

    out = asyncio.run(loader.invoke(infos[0], action="run", payload={"x": "shiny"}))
    assert out == "ran: shiny can_net=True"


def test_plugin_permission_denied(plugin_dir, tmp_path):
    from plugins.loader import PluginContext, PluginLoader

    loader = PluginLoader(plugins_dir=plugin_dir.parent)
    infos = loader.load_all(ctx=PluginContext(permissions=[], data_dir=str(tmp_path)))
    out = asyncio.run(
        loader.invoke(
            infos[0],
            payload={"x": "nope"},
            ctx=PluginContext(permissions=[]),  # manifest says network, host overrides
        )
    )
    assert "can_net=False" in out


def test_sandbox_timeout():
    async def slow():
        import asyncio

        await asyncio.sleep(10)
        return "late"

    sandbox = PluginSandbox(default_timeout=0.05)
    with pytest.raises(PluginError):
        asyncio.run(sandbox.call_async(slow()))


def test_sandbox_isolates_errors():
    async def boom():
        raise ZeroDivisionError("nope")

    sandbox = PluginSandbox()
    with pytest.raises(PluginError):
        asyncio.run(sandbox.call_async(boom()))
