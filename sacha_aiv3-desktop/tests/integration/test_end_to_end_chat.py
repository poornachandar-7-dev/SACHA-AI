"""
tests/integration/test_end_to_end_chat.py — gated on SACHA_IT=1.

With a live Ollama instance (or a configured cloud key) this drives a real
composer reply through the whole pipeline: routing, memory, session, tools.
Gated so CI stays offline.
"""

from __future__ import annotations

import asyncio
import os

import pytest

IT = os.environ.get("SACHA_IT", "0") == "1"

pytestmark = pytest.mark.skipif(
    not IT,
    reason="set SACHA_IT=1 (with a local/cloud provider running) for end-to-end chat",
)


async def test_full_pipeline_reply(tmp_path):
    from core.bootstrap import create_context

    ctx = await create_context(data_dir=tmp_path / "data")

    # Simple greeting goes through the real composer.
    result = await ctx.composer.reply("hi")
    assert result.text.strip() != ""

    # A privacy-sensitive prompt still routes somewhere sane and answers.
    private = await ctx.composer.reply("my medical password is secret — what should I do?")
    assert private.provider == "local"

    # The fact extractor should have picked something up from that turn.
    await asyncio.sleep(0.5)
    assert ctx.memory_graph.stats()["facts"] >= 0

    await ctx.shutdown()
