"""
Unit tests for LLM message assembly and response generation in VoiceDesk.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from llm import (
    _build_messages,
    generate_response,
    generate_response_async,
    generate_response_stream,
)
from memory import ConversationMemory


def test_build_messages_structure():
    memory = ConversationMemory(max_messages=5)
    memory.add_user("Previous user question")
    memory.add_assistant("Previous assistant response")

    messages = _build_messages(
        system_prompt="You are a test assistant.",
        memory=memory,
        user_text="Current user question",
    )

    assert len(messages) == 4
    assert messages[0] == {"role": "system", "content": "You are a test assistant."}
    assert messages[1] == {"role": "user", "content": "Previous user question"}
    assert messages[2] == {"role": "assistant", "content": "Previous assistant response"}
    assert messages[3] == {"role": "user", "content": "Current user question"}


def test_build_messages_without_memory():
    messages = _build_messages(
        system_prompt="System instructions",
        memory=None,
        user_text="User query",
    )

    assert len(messages) == 2
    assert messages[0] == {"role": "system", "content": "System instructions"}
    assert messages[1] == {"role": "user", "content": "User query"}


@pytest.mark.asyncio
async def test_generate_response_stream_empty_input():
    chunks = []
    async for chunk in generate_response_stream(
        user_text="   ",
        system_prompt="Be concise",
    ):
        chunks.append(chunk)

    full = "".join(chunks)
    assert "couldn't hear anything" in full.lower()


@pytest.mark.asyncio
async def test_generate_response_stream_offline(monkeypatch):
    monkeypatch.setattr("llm.get_async_groq_client", lambda: None)
    chunks = []
    async for chunk in generate_response_stream(
        user_text="Hello",
        system_prompt="Be concise",
    ):
        chunks.append(chunk)

    full = "".join(chunks)
    assert "offline mode" in full.lower()


@pytest.mark.asyncio
async def test_generate_response_stream_success(monkeypatch):
    class FakeDelta:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.delta = FakeDelta(content)

    class FakeChunk:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    async def fake_stream_generator():
        yield FakeChunk("Hello ")
        yield FakeChunk("world!")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_stream_generator())
    monkeypatch.setattr("llm.get_async_groq_client", lambda: mock_client)

    chunks = []
    async for chunk in generate_response_stream(
        user_text="Hi",
        system_prompt="Test persona",
    ):
        chunks.append(chunk)

    assert chunks == ["Hello ", "world!"]


@pytest.mark.asyncio
async def test_generate_response_stream_error_handling(monkeypatch):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("Groq service failure"))
    monkeypatch.setattr("llm.get_async_groq_client", lambda: mock_client)

    chunks = []
    async for chunk in generate_response_stream(
        user_text="Hi",
        system_prompt="Test persona",
    ):
        chunks.append(chunk)

    full = "".join(chunks)
    assert "encountered an issue" in full.lower()


@pytest.mark.asyncio
async def test_generate_response_async_direct(monkeypatch):
    mock_choice = MagicMock()
    mock_choice.message.content = "Direct response from LLaMA 3"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    monkeypatch.setattr("llm.get_async_groq_client", lambda: mock_client)

    reply = await generate_response_async(
        user_text="Tell me a fact",
        system_prompt="Test persona",
    )
    assert reply == "Direct response from LLaMA 3"


def test_generate_response_sync_wrapper(monkeypatch):
    mock_choice = MagicMock()
    mock_choice.message.content = "Sync wrapper response"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    monkeypatch.setattr("llm.get_async_groq_client", lambda: mock_client)

    reply = generate_response(
        user_text="Test prompt",
        system_prompt="Test persona",
    )
    assert reply == "Sync wrapper response"
