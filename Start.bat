@echo off
cd /d "%~dp0backend"
call SACHA.AI\Scripts\activate.bat
start /min "" uvicorn app:app --reload --host 0.0.0.0 --port 8000
timeout /t 3 >nul
start "" "%~dp0frontend\index.html"