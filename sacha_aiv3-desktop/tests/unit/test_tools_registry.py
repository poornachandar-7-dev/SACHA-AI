"""Unit tests — core/tools/registry.py + tool registry defaults."""

import asyncio

import pytest

from core.tools.base import Tool, ToolError


def test_default_tools_registered(tool_registry):
    names = tool_registry.names()
    for expected in ("open_website", "web_search", "open_app", "system_control", "clipboard", "screenshot", "run_command", "weather"):
        assert expected in names, f"{expected} missing from {names}"


def test_describe_all_shape(tool_registry):
    entries = tool_registry.describe_all()
    assert all({"name", "description", "parameters"}.issubset(e) for e in entries)


def test_unknown_tool_raises_keyerror(tool_registry):
    with pytest.raises(KeyError):
        tool_registry.get("nope")


def test_run_command_echo_is_allowlisted(tool_registry):
    result = asyncio.run(tool_registry.invoke_text("run_command", "echo hello sacha"))
    assert result.ok
    assert "hello sacha" in result.output


def test_run_command_rejects_non_allowlisted(tool_registry):
    result = asyncio.run(tool_registry.invoke_text("run_command", "format c:"))
    assert not result.ok
    assert "allowlist" in result.error


def test_tool_error_is_captured():
    class BrokenTool(Tool):
        name = "broken"

        async def run(self, **kwargs):
            raise ToolError("boom")

    result = asyncio.run(BrokenTool().invoke())
    assert result.ok is False
    assert "boom" in result.output


def test_register_duplicate_overwrites():
    from core.tools.registry import ToolRegistry

    class A(Tool):
        name = "dup"

        async def run(self, **kwargs):
            return "a"

    class B(Tool):
        name = "dup"

        async def run(self, **kwargs):
            return "b"

    reg = ToolRegistry()
    reg.register(A())
    reg.register(B())
    assert len(reg.names()) == 1
    assert asyncio.run(reg.invoke("dup")).output == "b"
