"""
VoiceDesk - FastAPI Real-time WebSocket Server

Handles duplex communication for speech recognition, LLM reasoning,
and streaming audio synthesis over WebSockets.
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from asr import transcribe_audio
from llm import DEFAULT_LLM_MODEL, generate_response_stream
from memory import ConversationMemory
from tts_stream import DEFAULT_VOICE, generate_audio_stream

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
)
logger = logging.getLogger("VoiceDesk.Server")

load_dotenv()

app = FastAPI(
    title="VoiceDesk Audio AI Server",
    description="Real-time voice assistant API with Groq Whisper ASR, LLaMA 3, and Edge TTS streaming.",
    version="1.2.0",
)

# Parse CORS origins from environment or default to common development URLs
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,*")
allowed_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_system_prompt() -> str:
    """Load default persona prompt from file or fallback to safe default."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
    if os.path.exists(prompt_path):
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as exc:
            logger.warning(f"Could not read prompt from {prompt_path}: {exc}")

    return (
        "You are VoiceDesk, an articulate and fast AI voice assistant. "
        "Keep your answers concise, friendly, and spoken-language friendly."
    )


@app.get("/")
async def root():
    """Root health check status."""
    return {
        "status": "online",
        "service": "VoiceDesk",
        "version": "1.2.0",
        "endpoints": {
            "health": "/health",
            "info": "/api/info",
            "websocket": "/ws/audio",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for liveness and readiness probes."""
    has_groq_key = bool(os.getenv("GROQ_API_KEY"))
    return {
        "status": "healthy" if has_groq_key else "degraded",
        "groq_configured": has_groq_key,
        "default_model": os.getenv("VOICEDESK_MODEL", DEFAULT_LLM_MODEL),
        "default_voice": os.getenv("VOICEDESK_VOICE", DEFAULT_VOICE),
    }


@app.get("/api/info")
async def server_info():
    """Return runtime metadata and active engine configuration."""
    return {
        "name": "VoiceDesk Real-Time Voice Engine",
        "model": os.getenv("VOICEDESK_MODEL", DEFAULT_LLM_MODEL),
        "voice": os.getenv("VOICEDESK_VOICE", DEFAULT_VOICE),
        "sample_rate": 16000,
        "format": "audio/wav",
    }


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    """
    WebSocket endpoint handling client audio payloads, transcription,
    streaming LLM completion, and streaming synthesized audio chunks.
    """
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info(f"Client connected from {client_ip}")

    memory = ConversationMemory(max_messages=20)
    system_prompt = load_system_prompt()

    try:
        while True:
            raw_data = await websocket.receive_text()

            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format received."}
                )
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "commit":
                audio_b64 = message.get("audio_data")
                if not audio_b64:
                    await websocket.send_json(
                        {"type": "error", "message": "Missing audio_data in commit payload."}
                    )
                    continue

                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception as b64_err:
                    logger.error(f"Base64 decode failure: {b64_err}")
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid base64 audio payload."}
                    )
                    continue

                # Write audio payload to a temporary file for ASR
                temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_filename = temp_file.name

                try:
                    temp_file.write(audio_bytes)
                    temp_file.flush()
                    temp_file.close()

                    # 1. Automatic Speech Recognition
                    await websocket.send_json({"type": "status", "state": "transcribing"})
                    user_text = await transcribe_audio(temp_filename)

                    if not user_text:
                        await websocket.send_json(
                            {"type": "error", "message": "No intelligible speech detected."}
                        )
                        await websocket.send_json({"type": "status", "state": "listening"})
                        continue

                    await websocket.send_json(
                        {"type": "transcription", "text": user_text, "role": "user"}
                    )
                    memory.add_user(user_text)

                    # 2. Interleaved LLM generation and Edge TTS streaming
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    full_response_text = ""

                    llm_stream = generate_response_stream(
                        user_text=user_text,
                        system_prompt=system_prompt,
                        memory=memory,
                    )

                    async def text_tapper(iterator):
                        nonlocal full_response_text
                        async for text_chunk in iterator:
                            full_response_text += text_chunk
                            await websocket.send_json(
                                {"type": "text_delta", "delta": text_chunk}
                            )
                            yield text_chunk

                    audio_stream = generate_audio_stream(text_tapper(llm_stream))

                    async for audio_chunk in audio_stream:
                        b64_audio = base64.b64encode(audio_chunk).decode("utf-8")
                        await websocket.send_json(
                            {"type": "audio_stream", "data": b64_audio}
                        )

                    # Persist final assistant response into memory
                    memory.add_assistant(full_response_text)
                    await websocket.send_json(
                        {"type": "response_complete", "text": full_response_text}
                    )
                    await websocket.send_json({"type": "status", "state": "listening"})

                except Exception as process_err:
                    logger.error(f"Error processing audio session: {process_err}")
                    await websocket.send_json(
                        {"type": "error", "message": "Internal error processing voice request."}
                    )
                    await websocket.send_json({"type": "status", "state": "listening"})

                finally:
                    if os.path.exists(temp_filename):
                        try:
                            os.remove(temp_filename)
                        except OSError:
                            pass

            elif msg_type == "clear_memory":
                memory.clear()
                await websocket.send_json({"type": "memory_cleared"})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected ({client_ip})")
    except Exception as exc:
        logger.error(f"WebSocket session terminated with error: {exc}")


def start_server():
    """CLI helper to boot the ASGI server using environment parameters."""
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting VoiceDesk server on http://{host}:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
