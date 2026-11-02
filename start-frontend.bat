@echo off
title VoiceDesk Web UI
cd /d "%~dp0frontend"
echo ===================================================
echo Starting VoiceDesk Next.js Frontend (http://localhost:3000)
echo ===================================================
npm run dev
pause
