"""
VoiceDesk - Audio Recording and Input Utilities

Provides safe microphone capture with dynamic device checks,
proper resource termination, and format configuration for Whisper ASR.
"""

import logging
import os
import wave
from typing import Optional

logger = logging.getLogger("VoiceDesk.Audio")


def is_microphone_available() -> bool:
    """Check if PyAudio is installed and at least one input device exists."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        try:
            device_count = pa.get_device_count()
            for i in range(device_count):
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    return True
            return False
        finally:
            pa.terminate()
    except Exception:
        return False


def record_microphone(
    output_path: str = "input.wav",
    duration_seconds: int = 5,
    rate: int = 16000,
    channels: int = 1,
    chunk_size: int = 1024,
) -> Optional[str]:
    """
    Record audio from the primary microphone into a 16kHz WAV file.

    :param output_path: Destination path for the WAV recording.
    :param duration_seconds: Total recording duration in seconds.
    :param rate: Sampling rate (16000 Hz recommended for Whisper).
    :param channels: Number of audio channels (1 = mono).
    :param chunk_size: Buffer size per read.
    :return: Path to the recorded file if successful, or None on failure.
    """
    try:
        import pyaudio
    except ImportError:
        logger.error(
            "PyAudio is not installed. To enable CLI microphone recording, install: pip install PyAudio"
        )
        return None

    audio_interface = None
    stream = None

    try:
        audio_interface = pyaudio.PyAudio()
        fmt = pyaudio.paInt16

        stream = audio_interface.open(
            format=fmt,
            channels=channels,
            rate=rate,
            input=True,
            frames_per_buffer=chunk_size,
        )

        logger.info(f"Recording microphone for {duration_seconds} seconds ({rate}Hz)...")
        frames = []
        total_chunks = int(rate / chunk_size * duration_seconds)

        for _ in range(total_chunks):
            data = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(data)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(audio_interface.get_sample_size(fmt))
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))

        logger.info(f"Recording successfully saved to: {output_path}")
        return output_path

    except Exception as exc:
        logger.error(f"Microphone recording failed: {exc}")
        return None

    finally:
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        if audio_interface is not None:
            try:
                audio_interface.terminate()
            except Exception:
                pass
