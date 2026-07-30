# sacha_aiv3-desktop

SACHA V3 — Smart Autonomous Cognitive Helper Assistant, desktop edition.

A native-window AI assistant built on the V3 architecture: pywebview HUD,
OmniRouter-driven provider selection, graph-based long-term memory, and an
async pipeline that supports wake-word listening, barge-in, and streaming
replies without a browser in the loop.

## Quick start

1. `python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in any provider keys you want to use.
4. `python launch.py`

## Project layout

See `docs/architecture.md` for the full V3 architecture diagram and how each
folder maps to it.

## Status

V3 in progress. See the Obsidian project notes for the full roadmap and
version history (V1 web app → V2 .bat-launched local server → V3 native
desktop).