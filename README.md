# SACHA — v1 (Text Chat + Memory + One Tool)

## What this version does
- Text chat with a local AI model via Ollama
- Remembers recent conversation (SQLite)
- One working tool: "open youtube" / "open google" / "open github" / "open gmail"
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

Type a message and hit Send or Enter. Try "open youtube" to see the tool-calling work.

## Project structure
```
sacha-ai/
├── backend/
│   ├── app.py          # FastAPI app, main entry point
│   ├── ai.py            # AI provider abstraction (Ollama by default)
│   ├── memory.py         # SQLite chat history
│   ├── tools.py           # Tool/automation logic (v1: open website)
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

## What's next (not built yet)
- Speech-to-text (faster-whisper) → speech.py
- Text-to-speech (Piper) → tts.py
- Wake word ("Hey SACHA")
- Vision module
- More tools (currently only "open website" works)
- Web-hosted demo mode (OpenAI/Gemini provider implementation)
