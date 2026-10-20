"""
Unit tests for ConversationMemory module in VoiceDesk.
"""

import pytest
from memory import ConversationMemory


def test_memory_initialization():
    mem = ConversationMemory(max_messages=5)
    assert len(mem) == 0
    assert mem.max_messages == 5
    assert mem.get_history() == []


def test_invalid_max_messages():
    with pytest.raises(ValueError):
        ConversationMemory(max_messages=0)

    with pytest.raises(ValueError):
        ConversationMemory(max_messages=-3)


def test_add_user_and_assistant_messages():
    mem = ConversationMemory(max_messages=4)
    mem.add_user("Hello, VoiceDesk!")
    mem.add_assistant("Hello! How can I assist you today?")

    history = mem.get_history()
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello, VoiceDesk!"}
    assert history[1] == {"role": "assistant", "content": "Hello! How can I assist you today?"}
    assert mem.get_last_user_message() == "Hello, VoiceDesk!"
    assert mem.get_last_assistant_message() == "Hello! How can I assist you today?"


def test_empty_string_ignored():
    mem = ConversationMemory(max_messages=4)
    mem.add_user("   ")
    mem.add_assistant("")
    assert len(mem) == 0


def test_rolling_window_trimming():
    mem = ConversationMemory(max_messages=3)
    mem.add_user("Message 1")
    mem.add_assistant("Message 2")
    mem.add_user("Message 3")
    assert len(mem) == 3

    # Adding a 4th message should drop Message 1
    mem.add_assistant("Message 4")
    assert len(mem) == 3

    history = mem.get_history()
    assert history[0]["content"] == "Message 2"
    assert history[1]["content"] == "Message 3"
    assert history[2]["content"] == "Message 4"


def test_defensive_history_copy():
    mem = ConversationMemory(max_messages=5)
    mem.add_user("Original")

    hist = mem.get_history()
    hist.append({"role": "user", "content": "Mutated"})

    assert len(mem.get_history()) == 1
    assert mem.get_history()[0]["content"] == "Original"


def test_serialization():
    mem = ConversationMemory(max_messages=8)
    mem.add_user("Test query")
    mem.add_assistant("Test answer")

    serialized = mem.to_dict()
    assert serialized["max_messages"] == 8
    assert len(serialized["messages"]) == 2

    reconstructed = ConversationMemory.from_dict(serialized)
    assert reconstructed.max_messages == 8
    assert reconstructed.get_history() == mem.get_history()


def test_clear_memory():
    mem = ConversationMemory(max_messages=5)
    mem.add_user("Hello")
    assert len(mem) == 1

    mem.clear()
    assert len(mem) == 0
    assert mem.get_history() == []
