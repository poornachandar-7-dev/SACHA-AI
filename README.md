# SACHA — v2 (Text Chat + Memory + Smarter Tooling)

## What's new in v2
- **`open_site` now falls back to a web search.** Previously, asking to open an unrecognized site (anything not in `KNOWN_SITES` and not a valid domain) returned an error. Now it opens a Google search for the term instead, so "open the weather" or "open some obscure app" still does something useful.
- **Fixed a memory/DB bug.** `memory.py` had a bug where `DB_PATH` silently fell back to the current working directory instead of `database/sacha.db` whenever `SACHA_DB_PATH` wasn't set (`Path("")` is truthy in Python, so the `or` fallback never triggered). This caused `sqlite3.OperationalError: unable to open database file` on `/chat`. Fixed by checking the env var as a string before wrapping it in `Path`.
- Everything else from v1 (text chat via Ollama, SQLite memory, tool calling for known sites) is unchanged and still works the same way.

## What this version does
- Text chat with a local AI model via Ollama
- Remembers recent conversation (SQLite)
- Working tools: "open youtube" / "open google" / "open github" / "open gmail" / "open linkedin" / "open twitter", plus **any other site or search term** (falls back to a web search)
- Speech, TTS, vision, wake word: NOT implemented yet (stub files only)

## Requirements
- Python 3.14 (or any 3.x you have installed)
- Ollama installed: https://ollama.com/download

## Setup

### 1. Install and start Ollama
Download Ollama, then in a terminal:
```
ollama serve
ollama pull llama3.2
```
Leave this terminal running.

### 2. Set up the backend
In a new terminal:
```
cd backend
python -m venv SACHA.AI
```
Activate the venv:
- Windows: `SACHA.AI\Scripts\activate`
- macOS/Linux: `source SACHA.AI/bin/activate`

Install dependencies:
```
pip install -r requirements.txt
```

Run the backend:
```
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

You should see it running at http://localhost:8000 — visiting that URL in a browser
should show `{"status": "SACHA backend is running"}`.

### 3. Open the frontend
No server needed for this part — just open `frontend/index.html` directly in your browser
(double-click it, or right-click → Open with browser).

Type a message and hit Send or Enter.
- Try "open youtube" to see a known-site tool call.
- Try "open some random thing" to see the new web-search fallback in action.

## Project structure
```
sacha-ai/
├── backend/
│   ├── app.py          # FastAPI app, main entry point
│   ├── ai.py            # AI provider abstraction (Ollama by default)
│   ├── memory.py         # SQLite chat history (DB_PATH bug fixed in v2)
│   ├── tools.py           # Tool/automation logic (v2: open website + web-search fallback)
│   ├── speech.py           # STT — not implemented yet
│   ├── tts.py               # TTS — not implemented yet
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── database/            # sacha.db created here automatically on first run
└── README.md
```

## Switching AI provider or model
In `backend/ai.py`, controlled by environment variables:
```
AI_PROVIDER=ollama        # ollama | openai | gemini | claude (only ollama is implemented)
OLLAMA_MODEL=llama3.2     # change to gemma3n:e4b etc.
```
Set these before running uvicorn, e.g.:
```
set OLLAMA_MODEL=gemma3n:e4b     (Windows PowerShell: $env:OLLAMA_MODEL="gemma3n:e4b")
export OLLAMA_MODEL=gemma3n:e4b  (macOS/Linux)
```

You can also override the database location:
```
SACHA_DB_PATH=/custom/path/to/sacha.db
```
If unset, it now correctly defaults to `database/sacha.db` at the project root, regardless of the working directory uvicorn is launched from.

## What's next (not built yet)
- Speech-to-text (faster-whisper) → speech.py
- Text-to-speech (Piper) → tts.py
- Wake word ("Hey SACHA")
- Vision module
- More native tools beyond open-site/web-search
- Web-hosted demo mode (OpenAI/Gemini provider implementation)