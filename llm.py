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
from utils.groq_client import get_async_groq_client

load_dotenv()

logger = logging.getLogger("VoiceDesk.LLM")

DEFAULT_LLM_MODEL = os.getenv("VOICEDESK_MODEL", "llama-3.3-70b-versatile")
DEFAULT_LLM_TIMEOUT = float(os.getenv("VOICEDESK_LLM_TIMEOUT", "30.0"))


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
    timeout: float = DEFAULT_LLM_TIMEOUT,
) -> AsyncGenerator[str, None]:
    """
    Generate a streaming conversational response token-by-token.

    :param user_text: Current user input.
    :param system_prompt: Persona or instructions.
    :param memory: Conversation memory instance.
    :param model: Groq LLM model name.
    :param temperature: Generation temperature.
    :param max_tokens: Maximum tokens in response.
    :param timeout: Request timeout in seconds.
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
        stream = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=True,
            ),
            timeout=timeout,
        )

        async for chunk in stream:
            choices = getattr(chunk, "choices", [])
            if choices and hasattr(choices[0], "delta"):
                token = getattr(choices[0].delta, "content", None)
                if token:
                    yield token

    except asyncio.TimeoutError:
        logger.error(f"LLM request timed out after {timeout} seconds.")
        yield "The request timed out. Please try again in a moment."
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
    timeout: float = DEFAULT_LLM_TIMEOUT,
) -> str:
    """
    Generate a complete LLM response asynchronously (non-streaming).
    Uses direct non-streaming completion when available for lowest latency.
    """
    clean_user_text = user_text.strip() if user_text else ""
    if not clean_user_text:
        return "I couldn't hear anything. Could you please repeat that?"

    client = get_async_groq_client()
    if client is None:
        return "I'm currently running in offline mode. Please configure your GROQ_API_KEY in .env."

    messages = _build_messages(system_prompt, memory, clean_user_text)

    try:
        completion = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            ),
            timeout=timeout,
        )
        choices = getattr(completion, "choices", [])
        if choices and hasattr(choices[0], "message"):
            content = getattr(choices[0].message, "content", "")
            if content:
                return content.strip()
    except Exception as exc:
        logger.warning(f"Direct non-streaming completion fallback: {exc}")

    # Fallback to streaming accumulator
    full_text = ""
    async for chunk in generate_response_stream(
        user_text=clean_user_text,
        system_prompt=system_prompt,
        memory=memory,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
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
    timeout: float = DEFAULT_LLM_TIMEOUT,
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
                timeout=timeout,
            )
        )
    except Exception as exc:
        logger.error(f"Sync LLM generation error: {exc}")
        return "I'm sorry, an error occurred while generating the response."
