# Packaging

SACHA ships as a single Windows `.exe` to start. macOS and Linux bundles
come later.

## Tooling

- **PyInstaller** for the Python half (`scripts/build.py`)
- **No Electron / no Chromium** — V3 dropped Electron in favor of
  pywebview, so we no longer ship a 100MB+ browser
- Ollama is **not** redistributed; the installer links to
  https://ollama.com/download and prompts the user on first run

## Build steps

1. `python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt -r requirements-dev.txt`
3. `python scripts/build.py`
4. Output lands in `dist/sacha-desktop/` with a `sacha-desktop.exe` entry
5. `python scripts/sign_windows.py` signs the binary (requires a code-sign
   cert; skip in dev)
6. `python scripts/smoke_test.py` launches the built binary, sends one
   chat message, and confirms a reply streams back

## First-run UX

- Installer places a desktop shortcut and an entry in the Start Menu
- First launch prompts for provider keys (NVIDIA / OpenAI / Gemini) — these
  are stored in the OS keyring, not in plaintext
- If Ollama isn't detected, the installer offers a deep link to download it

## Auto-updates

Not in v1.0. Manual download + reinstall. A delta-update channel is a
post-launch goal.

## What is NOT bundled

- Ollama itself (license + size)
- Local LLM model weights (downloaded on first use)
- Voice models for Piper / faster-whisper — these are pulled lazily on
  first voice interaction, not bundled