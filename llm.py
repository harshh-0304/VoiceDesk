import os
from typing import Optional, List, Dict, AsyncGenerator

from dotenv import load_dotenv
from groq import AsyncGroq

from memory import ConversationMemory

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in .env")

client = AsyncGroq(api_key=GROQ_API_KEY)

# Fast, smart LLM model from Groq
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"


def _build_messages(
    system_prompt: str,
    memory: Optional[ConversationMemory],
    user_text: str,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if memory:
        messages.extend(memory.get_history())

    messages.append({"role": "user", "content": user_text})

    return messages


async def generate_response_stream(
    user_text: str,
    system_prompt: str,
    memory: Optional[ConversationMemory] = None,
    model: str = DEFAULT_LLM_MODEL,
) -> AsyncGenerator[str, None]:
    """
    Calls Groq Llama 3 to generate a smart conversational response (Streaming).
    Yields text chunks.
    """

    user_text = user_text.strip()
    if not user_text:
        yield "I couldn't hear anything. Could you please repeat that?"
        return

    messages = _build_messages(system_prompt, memory, user_text)

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=512,
            stream=True,
        )

        full_reply = ""
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                full_reply += token
                yield token

        print(f"[VoiceDesk] LLM reply: {full_reply}")
        # Note: We can't update memory here easily because it's a generator.
        # The caller should handle memory update after consuming the stream.
        # Or we can update it at the end?
        # Let's return the full text? No, generator can't return.
        # Caller handles memory.

    except Exception as e:
        print(f"[VoiceDesk] LLM error: {e}")
        yield "Sorry, something went wrong while generating a response."
