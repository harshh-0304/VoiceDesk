"""
VoiceDesk - Shared Groq client bootstrap.

Both the ASR and LLM modules talk to Groq Cloud; this provides a single
lazily-instantiated, cached AsyncGroq client so credentials and imports are
resolved in exactly one place.
"""

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from groq import AsyncGroq

logger = logging.getLogger("VoiceDesk.Groq")

_async_groq_client = None


def get_async_groq_client() -> Optional["AsyncGroq"]:
    """Lazily instantiate and cache a shared AsyncGroq client, or None."""
    global _async_groq_client
    if _async_groq_client is not None:
        return _async_groq_client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY is not configured in environment or .env file.")
        return None

    try:
        from groq import AsyncGroq
        _async_groq_client = AsyncGroq(api_key=api_key)
        return _async_groq_client
    except ImportError:
        logger.error("The 'groq' package is not installed. Install with: pip install groq")
        return None
