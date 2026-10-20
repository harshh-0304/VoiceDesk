"""
VoiceDesk - Large Language Model (LLM) Integration

Powers the conversational intelligence of VoiceDesk using Groq Cloud
with Llama 3 models (e.g. llama-3.3-70b-versatile).
Provides streaming and non-streaming responses for both WebSocket and CLI interfaces.
"""

import asyncio
import logging
import os
from typing import AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from memory import ConversationMemory

load_dotenv()

logger = logging.getLogger("VoiceDesk.LLM")

DEFAULT_LLM_MODEL = os.getenv("VOICEDESK_MODEL", "llama-3.3-70b-versatile")
_async_groq_client = None


def get_async_groq_client():
    """Lazily instantiate and cache the AsyncGroq client."""
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


def _build_messages(
    system_prompt: str,
    memory: Optional[ConversationMemory],
    user_text: str,
) -> List[Dict[str, str]]:
    """Assemble context history and user query into chat schema."""
    messages: List[Dict[str, str]] = []

    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    if memory is not None:
        messages.extend(memory.get_history())

    messages.append({"role": "user", "content": user_text.strip()})
    return messages


async def generate_response_stream(
    user_text: str,
    system_prompt: str,
    memory: Optional[ConversationMemory] = None,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> AsyncGenerator[str, None]:
    """
    Generate a streaming conversational response token-by-token.

    :param user_text: Current user input.
    :param system_prompt: Persona or instructions.
    :param memory: Conversation memory instance.
    :param model: Groq LLM model name.
    :param temperature: Generation temperature.
    :param max_tokens: Maximum tokens in response.
    :return: Async generator yielding text deltas.
    """
    clean_user_text = user_text.strip() if user_text else ""
    if not clean_user_text:
        yield "I couldn't hear anything. Could you please repeat that?"
        return

    client = get_async_groq_client()
    if client is None:
        yield "I'm currently running in offline mode. Please configure your GROQ_API_KEY in .env."
        return

    messages = _build_messages(system_prompt, memory, clean_user_text)

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            choices = getattr(chunk, "choices", [])
            if choices and hasattr(choices[0], "delta"):
                token = getattr(choices[0].delta, "content", None)
                if token:
                    yield token

    except Exception as exc:
        logger.error(f"LLM streaming generation error: {exc}")
        yield "Sorry, I encountered an issue processing your request."


async def generate_response_async(
    user_text: str,
    system_prompt: str,
    memory: Optional[ConversationMemory] = None,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> str:
    """
    Generate a complete LLM response asynchronously (non-streaming).
    """
    full_text = ""
    async for chunk in generate_response_stream(
        user_text=user_text,
        system_prompt=system_prompt,
        memory=memory,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        full_text += chunk
    return full_text.strip()


def generate_response(
    user_text: str,
    system_prompt: str,
    memory: Optional[ConversationMemory] = None,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> str:
    """
    Synchronous wrapper for generating LLM responses, used by CLI scripts.
    """
    try:
        return asyncio.run(
            generate_response_async(
                user_text=user_text,
                system_prompt=system_prompt,
                memory=memory,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )
    except Exception as exc:
        logger.error(f"Sync LLM generation error: {exc}")
        return "I'm sorry, an error occurred while generating the response."
