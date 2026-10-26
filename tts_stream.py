"""
VoiceDesk - Real-time Streaming Text-to-Speech Engine

Leverages Microsoft Edge TTS for low-latency, neural speech generation.
Buffers incoming streaming tokens from LLMs and streams complete audio frames.
"""

import logging
import os
import re
from typing import AsyncGenerator, Optional

logger = logging.getLogger("VoiceDesk.TTSStream")

DEFAULT_VOICE = os.getenv("VOICEDESK_VOICE", "en-US-ChristopherNeural")
PUNCTUATION_SPLIT_REGEX = re.compile(r"([.!?\n]+)")


async def _stream_text_chunk(text: str, voice: str) -> AsyncGenerator[bytes, None]:
    """Helper to stream audio frames for a synthesized clause or sentence."""
    clean_text = text.strip()
    if not clean_text:
        return

    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts is not installed. Run: pip install edge-tts")
        return

    try:
        communicate = edge_tts.Communicate(clean_text, voice)
        full_audio = b""
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and "data" in chunk:
                full_audio += chunk["data"]

        if full_audio:
            yield full_audio

    except Exception as exc:
        logger.error(f"Error during edge-tts synthesis: {exc}")


async def generate_audio_stream(
    text_iterator: AsyncGenerator[str, None],
    voice: Optional[str] = None,
) -> AsyncGenerator[bytes, None]:
    """
    Consumes an async generator of LLM tokens, buffers them into conversational
    thought boundaries, and yields audio bytes (MP3 frame chunks) for real-time playback.

    :param text_iterator: Stream of token deltas from LLM.
    :param voice: Neural voice identifier (falls back to DEFAULT_VOICE).
    :return: Stream of binary MP3 audio frames.
    """
    selected_voice = voice or DEFAULT_VOICE
    buffer = ""

    try:
        async for chunk in text_iterator:
            buffer += chunk

            # Check if we have complete sentences or thought boundaries
            # Avoid prematurely splitting on short strings or decimals
            if len(buffer) >= 15 and any(punct in buffer for punct in [".", "!", "?", "\n"]):
                parts = PUNCTUATION_SPLIT_REGEX.split(buffer)
                # Keep everything up to the last split delimiter
                if len(parts) > 2:
                    to_synthesize = "".join(parts[:-1]).strip()
                    buffer = parts[-1]
                    if to_synthesize:
                        async for audio_chunk in _stream_text_chunk(to_synthesize, selected_voice):
                            yield audio_chunk

        # Process any trailing content in the buffer
        remaining = buffer.strip()
        if remaining:
            async for audio_chunk in _stream_text_chunk(remaining, selected_voice):
                yield audio_chunk

    except Exception as exc:
        logger.error(f"Streaming audio pipeline error: {exc}")


async def tts_to_file(
    text: str,
    output_file: str,
    voice: Optional[str] = None,
) -> bool:
    """
    Synthesize text directly into an audio file asynchronously.

    :param text: Text to speak.
    :param output_file: Target audio file path.
    :param voice: Voice identifier.
    :return: True if successful, False otherwise.
    """
    try:
        import edge_tts
        selected_voice = voice or DEFAULT_VOICE
        communicate = edge_tts.Communicate(text, selected_voice)
        await communicate.save(output_file)
        return True
    except Exception as exc:
        logger.error(f"Failed to save TTS audio file: {exc}")
        return False
