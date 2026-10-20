"""
VoiceDesk - Text-to-Speech (TTS) File Engine

Provides local audio synthesis with optional ffmpeg-based speed adjustment
and safe process execution.
"""

import logging
import os
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger("VoiceDesk.TTS")


def text_to_speech(
    text: str,
    output_path: str = "reply.mp3",
    lang: str = "en",
    speed: float = 1.25,
) -> Optional[str]:
    """
    Synthesize text to an MP3 file using Google TTS with optional ffmpeg speed acceleration.

    :param text: The text to be converted to speech.
    :param output_path: Destination path for the audio file.
    :param lang: Language code (e.g. 'en').
    :param speed: Audio playback speed multiplier (e.g. 1.25).
    :return: Path to the generated audio file, or None if generation failed.
    """
    clean_text = text.strip() if text else ""
    if not clean_text:
        logger.warning("Empty text passed to text_to_speech; skipping synthesis.")
        return None

    try:
        from gtts import gTTS
    except ImportError:
        logger.error("gTTS is not installed. Run: pip install gTTS")
        return None

    try:
        # Generate base audio
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        tts.save(output_path)

        # If natural speed requested or speed is 1.0, return standard output
        if abs(speed - 1.0) < 0.05:
            return output_path

        # Check if ffmpeg is available for speed adjustment
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            logger.debug("ffmpeg not found in PATH; using default audio speed.")
            return output_path

        base_dir = os.path.dirname(os.path.abspath(output_path))
        fast_output = os.path.join(base_dir, f"fast_{os.path.basename(output_path)}")

        speed_args = [
            ffmpeg_bin,
            "-y",
            "-i",
            output_path,
            "-filter:a",
            f"atempo={speed:.2f}",
            fast_output,
        ]

        result = subprocess.run(
            speed_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        if result.returncode == 0 and os.path.exists(fast_output):
            return fast_output

        return output_path

    except Exception as exc:
        logger.error(f"TTS synthesis failed: {exc}")
        return None
