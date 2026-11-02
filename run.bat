@echo off
title VoiceDesk CLI
cd /d "%~dp0"
echo ===================================================
echo Launching VoiceDesk Interactive CLI
echo ===================================================
.venv\Scripts\python.exe main.py
pause
