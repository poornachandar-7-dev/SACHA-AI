"""
launch.py — desktop entry point: starts backend, opens HUD.

Usage:
    python launch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when run from anywhere.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import main  # noqa: E402

if __name__ == "__main__":
    main()
