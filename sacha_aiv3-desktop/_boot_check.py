"""Temporary boot validation for sacha_aiv3-desktop (not committed)."""
import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.bootstrap import create_context
from core.config import Settings


async def main() -> None:
    s = Settings(data_dir=Path(tempfile.mkdtemp()) / "data", env="test", log_level="WARNING")
    ctx = await create_context(settings=s)
    d = ctx.describe()
    print(
        "ENGINE_BOOT_OK tools=%d providers=%s facts=%d session=%d background=%d"
        % (len(d["tools"]), d["router"]["configured_providers"], d["memory"]["facts"],
           d["session"]["message_count"], len(ctx._background_tasks))
    )
    print("presets:", ctx.personality.list_presets())
    print("tools:", ", ".join(d["tools"][:6]), "...")
    # Streaming against a non-running Ollama should end with a graceful error event.
    async for ev in ctx.composer.stream("hi"):
        if ev.get("type") in ("done", "error"):
            print("stream end event:", ev.get("type"))
    await ctx.shutdown()
    print("ENGINE_SHUTDOWN_OK")


if __name__ == "__main__":
    asyncio.run(main())