"""
scripts/build.py — PyInstaller bundle of the desktop HUD.

Produces a one-folder build in dist/ that ships the app + engine without a
Python install. Run from the project root:
    python scripts/build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "launch.py"

HIDDEN_IMPORTS = [
    "core",
    "app",
    "voice",
    "vision",
    "personality",
    "scheduler",
    "bridges",
    "plugins",
    "core.providers",
    "core.router",
    "core.memory",
    "core.memory.store",
    "core.reply",
    "core.conversation",
    "core.tools",
]


def main() -> int:
    if not ENTRY.exists():
        print("[build] launch.py not found at", ENTRY)
        return 1
    if shutil.which("pyinstaller") is None:
        print("[build] pyinstaller is not installed (pip install -r requirements-dev.txt)")
        return 1

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name", "SACHA_V3",
        "--collect-data", "pywebview",
        "--add-data", f"{ROOT / 'app' / 'hud.html'};app",
        "--hidden-import", "webview.platforms.edgechromium",
        "--hidden-import", "webview.platforms.winforms",
        *[f"--hidden-import={m}" for m in HIDDEN_IMPORTS],
        str(ENTRY),
    ]
    print("[build]", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
