"""
scripts/smoke_test.py — post-build sanity check.

Verifies, without opening a window:
1. every module imports
2. settings parse + directories materialize
3. the router classifies + picks a provider
4. memory graph round-trips a fact
5. an end-to-end composer reply works (against a fake provider)

Usage:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Import gate — if any of these fail, packaging is broken.
IMPORT_PROBE = [
    "core.config", "core.bootstrap", "core.providers.registry", "core.providers.local",
    "core.providers.openai", "core.providers.nvidia", "core.providers.gemini",
    "core.router.omni_router", "core.router.classifier", "core.router.fallback",
    "core.memory.graph", "core.memory.extractor", "core.memory.retriever", "core.memory.decay",
    "core.memory.store.graph_store", "core.conversation.session", "core.conversation.persistence",
    "core.reply.composer", "core.reply.context", "core.reply.streaming",
    "core.tools.registry", "core.tools.weather", "core.tools.run_command",
    "voice.stt", "voice.tts", "voice.wakeword", "voice.barge_in",
    "vision.gesture.pipeline", "vision.airdraw.canvas",
    "personality.loader", "scheduler.scheduler", "bridges.registry", "plugins.loader",
]


def _notify(msg: str) -> None:
    print(f"[smoke] {msg}")


def main() -> int:
    import sys

    sys.path.insert(0, str(PROJECT_ROOT))
    started = time.perf_counter()
    failures: list[str] = []

    # 1 — imports
    for module in IMPORT_PROBE:
        try:
            __import__(module)
        except Exception as exc:  # pragma: no cover
            failures.append(f"import {module}: {exc}")
    _notify(f"imports: {len(IMPORT_PROBE) - len(failures)}/{len(IMPORT_PROBE)} ok")
    if failures:
        for f in failures:
            print("   ", f)
        return 1

    # 2 — settings + dirs
    from core.config import Settings

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_dir=Path(tmp) / "data")
        settings.ensure_dirs()
        if not settings.data_dir.exists():
            failures.append("settings data_dir missing")
        _notify("settings + dirs ok")

        # 3 — router classifies
        from core.providers.registry import ProviderRegistry
        from core.router.classifier import KeywordClassifier
        from core.router.omni_router import OmniRouter

        registry = ProviderRegistry(settings)
        registry.register_defaults()
        router = OmniRouter(registry, KeywordClassifier())
        assert router.choose_provider("what is the airspeed of an unladen swallow") in registry.names()
        assert router.choose_provider("hi") == "local"
        _notify(f"router ok (providers: {registry.configured_names()})")

        # 4 — memory graph round-trip
        from core.memory.extractor import FactExtractor
        from core.memory.graph import MemoryFact, MemoryGraph
        from core.memory.retriever import MemoryRetriever

        graph = MemoryGraph.open(settings.graph_db_path)
        graph.add_fact(MemoryFact(content="identity: Alice", entities=["Alice"], relation="identity", confidence=0.95))
        retriever = MemoryRetriever(graph)
        assert "Alice" in retriever.context_block("who is alice?")
        extractor = FactExtractor(graph)
        facts = extractor.extract_from_text("My name is Bob and I love coffee")
        assert any(f.relation == "identity" for f in facts)
        graph.close()
        _notify("memory graph ok")

    # 5 — composer against a fake provider
    async def _composer_smoke() -> None:
        from core.conversation.session import Session
        from core.providers.base import ModelProvider
        from core.reply.composer import ReplyComposer
        from core.reply.context import ContextBuilder
        from core.router.fallback import FallbackChain
        from personality.loader import PersonalityLoader

        class FakeProvider(ModelProvider):
            name = "fake"
            default_model = "fake-1"

            async def generate(self, messages, **kwargs):
                return "fake reply: ok"

        reg = ProviderRegistry(settings)
        reg.register(FakeProvider())
        session = Session()
        composer = ReplyComposer(
            router=OmniRouter(reg, KeywordClassifier()),
            fallback=FallbackChain(reg),
            context_builder=ContextBuilder(PersonalityLoader()),
            session=session,
        )
        result = await composer.reply("hello")
        assert result.text == "fake reply: ok"
        assert len(session) == 2

    asyncio.run(_composer_smoke())
    _notify("composer ok")

    if failures:
        _notify(f"FAILED: {len(failures)} issue(s)")
        return 1
    _notify("all smoke checks passed in %.1fs" % (time.perf_counter() - started))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
