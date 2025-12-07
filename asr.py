import os
import aiofiles
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in .env")

client = AsyncGroq(api_key=GROQ_API_KEY)


async def transcribe_audio(file_path: str) -> str:
    """
    Uses Groq Whisper (whisper-large-v3-turbo) to transcribe a WAV/MP3 file.
    Returns plain text.
    """
    try:
        # Open file async? Groq client might need file object.
        # Standard open() is blocking, but for small files it's okay-ish.
        # Better: run in thread pool if strict async needed,
        # but Groq's .create() does async network I/O which is the bottleneck.
        # We'll use standard open for simplicity, it's brief.
        with open(file_path, "rb") as f:
            transcription = await client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3-turbo",  # fast + accurate model from Groq
                response_format="json",
                temperature=0.0,
            )
        text = transcription.text.strip()
        print(f"[VoiceDesk] Transcription: {text}")
        return text
    except Exception as e:
        print(f"[VoiceDesk] ASR error: {e}")
        return ""
