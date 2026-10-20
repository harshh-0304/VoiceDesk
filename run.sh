#!/usr/bin/env bash
# ==============================================================================
# VoiceDesk - Quick Start Launcher
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================================="
echo "          VoiceDesk - Neural Voice Assistant              "
echo "=========================================================="

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[*] No .env found. Generating .env from .env.example..."
        cp .env.example .env
        echo "[!] Please edit .env to set your GROQ_API_KEY if needed."
    fi
fi

case "$1" in
    cli)
        echo "[*] Launching VoiceDesk Interactive CLI..."
        python3 main.py
        ;;
    server)
        echo "[*] Starting VoiceDesk ASGI WebSocket Server..."
        python3 server.py
        ;;
    test)
        echo "[*] Running Test Suite..."
        python3 -m pytest tests/ -v
        ;;
    frontend)
        echo "[*] Starting Next.js Frontend Dashboard..."
        cd frontend && npm run dev
        ;;
    *)
        echo "Usage: ./run.sh [cli | server | frontend | test]"
        echo "Defaulting to server..."
        python3 server.py
        ;;
esac
