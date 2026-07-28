@echo off
echo Starting SACHA backend...

REM Activate the virtual environment
call SACHA.AI\Scripts\activate.bat

REM Start Ollama in a new window (if not already running)
start "Ollama" cmd /k "ollama serve"

REM Give Ollama a moment to start
timeout /t 3 /nobreak >nul

REM Start the FastAPI backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000