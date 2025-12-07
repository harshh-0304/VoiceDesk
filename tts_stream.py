import edge_tts
import tempfile
import asyncio
from typing import AsyncGenerator

# Voices:
# en-US-ChristopherNeural (Male, Deep)
# en-US-EricNeural (Male, Friendly)
# en-GB-SoniaNeural (Female, British)
# en-US-AnaNeural (Female, Child-like)
VOICE = "en-US-ChristopherNeural"

async def generate_audio_stream(text_iterator: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
    """
    Consumes an async generator of text (from LLM) and yields audio bytes (MP3 frame chunks).
    """
    # communicate = edge_tts.Communicate()  <-- This was the bug. Removed.
    
    # We need to buffer text slightly to avoid weird artifacts with very short tokens
    buffer = ""
    
    async for chunk in text_iterator:
        buffer += chunk
        # Heuristic: split on punctuation to send complete "thoughts" to TTS
        if any(punct in buffer for punct in [".", "!", "?", ",", "\n"]):
            async for audio_chunk in _stream_text_chunk(buffer):
                yield audio_chunk
            buffer = ""
            
    # Process remaining buffer
    if buffer.strip():
        async for audio_chunk in _stream_text_chunk(buffer):
            yield audio_chunk

async def _stream_text_chunk(text: str) -> AsyncGenerator[bytes, None]:
    """Helper to stream audio for a single text block."""
    if not text.strip():
        return
        
    communicate = edge_tts.Communicate(text, VOICE)
    
    # ACCUMULATE all chunks for this sentence to ensure valid MP3 header/structure
    # when decoded by frontend AudioContext.
    full_audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            full_audio += chunk["data"]
            
    if full_audio:
        yield full_audio

async def tts_to_file(text: str, output_file: str) -> None:
    """Simple one-shot TTS for testing."""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)
