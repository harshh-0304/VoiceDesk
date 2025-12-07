import asyncio
import base64
import json
import logging
import os
import tempfile
import uuid
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from asr import transcribe_audio
from llm import generate_response_stream
from tts_stream import generate_audio_stream
from memory import ConversationMemory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceDeskServer")

load_dotenv()

app = FastAPI(title="VoiceDesk Shadow Monarch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global memory storage (simple in-memory for now, keyed by session_id if needed)
# For this demo, we'll create a new memory per connection
# or we could make it global. Let's make it per connection.

@app.get("/")
async def root():
    return {"message": "VoiceDesk Shadow Monarch Edition is Online"}

@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")

    memory = ConversationMemory(max_messages=20)
    system_prompt = (
        "You are VoiceDesk, an evolved AI assistant. "
        "You are fast, intelligent, and helpful. "
        "Keep responses concise and conversational."
    )
    
    # Validation loop
    try:
        while True:
            # Protocol: expecting JSON messages or raw bytes?
            # Let's use JSON for metadata and base64 for audio, or mixed.
            # Simpler: Client sends JSON `{"audio_data": "base64..."}` or `{"control": "commit"}`
            
            # Message format:
            # { "type": "audio_chunk", "data": "base64..." }
            # { "type": "commit" } -> user stopped talking, process buffer
            
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "audio_chunk":
                # We'll need a way to accumulate audio. 
                # For V1, let's assume the frontend sends the specific "commit" with the FULL audio 
                # or we buffer here. Let's buffer here.
                # Actually, easier: Client sends "commit" with the full audio blob to avoid server complexity?
                # No, streaming upload is better.
                pass 
                
            elif message["type"] == "commit":
                # The client signals that speech has ended and we should process the buffered audio.
                # Or the client sends the full audio in one go with "commit".
                # Let's support the latter for simplicity in V1 (User speaks, local VAD detects silence, sends full blob).
                
                audio_b64 = message.get("audio_data")
                if not audio_b64:
                    continue
                
                # Decode and save to temp file for ASR
                audio_bytes = base64.b64decode(audio_b64)
                temp_filename = f"temp_{uuid.uuid4()}.wav"
                
                try:
                    with open(temp_filename, "wb") as f:
                        f.write(audio_bytes)
                        
                    # 1. ASR
                    user_text = await transcribe_audio(temp_filename)
                    if not user_text:
                        await websocket.send_json({"type": "error", "message": "No speech detected"})
                        continue
                        
                    await websocket.send_json({"type": "transcription", "text": user_text, "role": "user"})
                    memory.add_user(user_text)
                    
                    # 2. LLM + 3. TTS (interleaved streaming)
                    # We need to collect the full text for memory updating later
                    full_response_text = ""
                    
                    # Create the AsyncGenerator for LLM text chunks
                    llm_stream = generate_response_stream(
                        user_text=user_text,
                        system_prompt=system_prompt,
                        memory=memory
                    )
                    
                    # Process the Audio Stream
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    
                    # We'll use a queue to send LLM chunks to the TTS generator?
                    # `generate_audio_stream` takes an async iterator. `llm_stream` IS an async iterator.
                    # Perfect chainer.
                    
                    # But we also need to capture the text for `full_response_text`.
                    # We can wrap the `llm_stream` to tap into the values.
                    
                    async def text_tapper(iterator):
                        nonlocal full_response_text
                        async for text_chunk in iterator:
                            full_response_text += text_chunk
                            # Emit text delta to frontend
                            await websocket.send_json({"type": "text_delta", "delta": text_chunk})
                            yield text_chunk

                    audio_stream = generate_audio_stream(text_tapper(llm_stream))
                    
                    async for audio_chunk in audio_stream:
                        # Send audio chunk to frontend
                        # base64 encode
                        b64_audio = base64.b64encode(audio_chunk).decode('utf-8')
                        await websocket.send_json({"type": "audio_stream", "data": b64_audio})
                    
                    # Done
                    memory.add_assistant(full_response_text)
                    await websocket.send_json({"type": "status", "state": "listening"})
                    
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        
            elif message["type"] == "ping":
                 await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
