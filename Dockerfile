# VoiceDesk backend (FastAPI WebSocket server)
FROM python:3.12-slim

# ffmpeg powers the optional TTS speed adjustment in tts.py
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

CMD ["python3", "server.py"]
