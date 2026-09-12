@echo off
REM sacha_aiv3-desktop — Windows one-click launcher
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [SACHA] Creating virtual environment...
    python -m venv .venv || goto :error
)

call ".venv\Scripts\activate.bat"
python launch.py
exit /b %errorlevel%

:error
echo [SACHA] Failed to set up the virtual environment. Please install Python 3.12+.
pause
exit /b 1