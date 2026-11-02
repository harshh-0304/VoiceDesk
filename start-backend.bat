@echo off
title VoiceDesk Backend
cd /d "%~dp0"
echo ===================================================
echo Starting VoiceDesk FastAPI Backend (http://localhost:8000)
echo ===================================================
call .venv\Scripts\activate.bat
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
pause
