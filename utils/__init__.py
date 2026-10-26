"""VoiceDesk utility package (audio capture and input helpers)."""

from utils.audio import is_microphone_available, record_microphone
from utils.groq_client import get_async_groq_client

__all__ = [
    "is_microphone_available",
    "record_microphone",
    "get_async_groq_client",
]
