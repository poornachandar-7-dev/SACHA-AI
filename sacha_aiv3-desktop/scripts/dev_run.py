"""
scripts/dev_run.py — run with hot-reload.

Watches the project for .py / .html / .js changes and restarts the HUD
process automatically. Keeps the dev loop to two files: this script and
launch.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCH_GLOBS = ("**/*.py", "**/*.html", "**/*.css", "**/*.js")
EXTENSIONS = {".py", ".html", ".css", ".js"}
IGNORED = {".venv", "__pycache__", ".git", "data", "build", "dist", "node_modules"}


def _snapshot() -> dict[str, tuple[int, float]]:
    """Path → (mtime_ns, size) for every watched file (cheap polling)."""
    snap: dict[str, tuple[int, float]] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        if any(part in IGNORED for part in path.parts):
            continue
        stat = path.stat()
        snap[str(path)] = (stat.st_mtime_ns, stat.st_size)
    return snap


def main() -> int:
    python = sys.executable
    snap = _snapshot()
    proc: subprocess.Popen | None = None

    def _spawn() -> subprocess.Popen:
        env = dict(os.environ, SACHA_HOT_RELOAD="1")
        return subprocess.Popen([python, str(ROOT / "launch.py")], env=env, cwd=str(ROOT))

    print(f"[dev_run] watching {ROOT} — Ctrl+C to stop")
    try:
        while True:
            if proc is None or proc.poll() is not None:
                print("[dev_run] (re)starting SACHA…")
                proc = _spawn()
            time.sleep(0.6)
            current = _snapshot()
            if current != snap and proc is not None and proc.poll() is None:
                print("[dev_run] change detected — restarting…")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                snap = current
                proc = None
    except KeyboardInterrupt:
        print("\n[dev_run] stopping")
        if proc is not None and proc.poll() is None:
            proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
