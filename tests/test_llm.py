"""
Unit tests for LLM message assembly in VoiceDesk.
"""

from llm import _build_messages
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
