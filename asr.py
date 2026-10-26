"""
VoiceDesk - Automatic Speech Recognition (ASR)

Leverages Groq Cloud Whisper (whisper-large-v3-turbo) for ultra-fast,
high-accuracy audio transcription with async and sync interfaces.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from utils.groq_client import get_async_groq_client

load_dotenv()

logger = logging.getLogger("VoiceDesk.ASR")

DEFAULT_ASR_MODEL = "whisper-large-v3-turbo"


async def transcribe_audio(
    file_path: str,
    model: str = DEFAULT_ASR_MODEL,
    temperature: float = 0.0,
) -> str:
    """
    Transcribe audio file using Groq Whisper.

    :param file_path: Path to the WAV or MP3 audio file.
    :param model: Whisper model identifier.
    :param temperature: Sampling temperature for Whisper decoding.
    :return: Transcribed text string, or empty string on failure.
    """
    if not os.path.exists(file_path):
        logger.error(f"Audio file does not exist: {file_path}")
        return ""

    if os.path.getsize(file_path) == 0:
        logger.warning(f"Audio file is empty: {file_path}")
        return ""

    client = get_async_groq_client()
    if client is None:
        logger.error("Cannot transcribe: Groq client is unavailable.")
        return ""

    try:
        with open(file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                response_format="json",
                temperature=temperature,
            )

        text = getattr(transcription, "text", "").strip()
        logger.info(f"Transcribed ({os.path.basename(file_path)}): {text}")
        return text

    except Exception as exc:
        logger.error(f"ASR transcription error: {exc}")
        return ""


def transcribe_audio_sync(
    file_path: str,
    model: str = DEFAULT_ASR_MODEL,
    temperature: float = 0.0,
) -> str:
    """Synchronous convenience wrapper around transcribe_audio."""
    try:
        return asyncio.run(
            transcribe_audio(file_path=file_path, model=model, temperature=temperature)
        )
    except Exception as exc:
        logger.error(f"Sync ASR transcription error: {exc}")
        return ""
