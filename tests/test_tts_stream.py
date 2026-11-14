"""
Unit tests for real-time streaming Edge-TTS pipeline in VoiceDesk.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from tts_stream import (
    _stream_text_chunk,
    generate_audio_stream,
    split_thought_boundaries,
    tts_to_file,
)


def test_split_thought_boundaries():
    ready, remaining = split_thought_boundaries("Short. ")
    assert ready == ""
    assert remaining == "Short. "

    ready, remaining = split_thought_boundaries("This is a complete sentence. Now trailing words")
    assert ready == "This is a complete sentence."
    assert remaining == "Now trailing words"

    ready, remaining = split_thought_boundaries("Value is 3.14 without delimiter")
    assert ready == ""
    assert remaining == "Value is 3.14 without delimiter"


@pytest.mark.asyncio
async def test_stream_text_chunk_empty():
    chunks = []
    async for chunk in _stream_text_chunk("", "en-US-ChristopherNeural"):
        chunks.append(chunk)
    assert chunks == []


@pytest.mark.asyncio
async def test_generate_audio_stream_sentence_buffering(monkeypatch):
    mock_chunks = [b"audio_part_1", b"audio_part_2"]

    async def fake_stream_chunk(text, voice):
        for c in mock_chunks:
            yield c

    monkeypatch.setattr("tts_stream._stream_text_chunk", fake_stream_chunk)

    async def token_generator():
        yield "Hello there! "
        yield "Welcome to VoiceDesk. "
        yield "How can I help you today?"

    received_audio = []
    async for audio_bytes in generate_audio_stream(token_generator()):
        received_audio.append(audio_bytes)

    assert len(received_audio) > 0
    assert mock_chunks[0] in received_audio


@pytest.mark.asyncio
async def test_tts_to_file_success(monkeypatch, tmp_path):
    output_path = str(tmp_path / "stream_out.mp3")

    fake_comm = MagicMock()
    fake_comm.save = AsyncMock(return_value=None)

    fake_edge_tts = MagicMock()
    fake_edge_tts.Communicate = MagicMock(return_value=fake_comm)

    monkeypatch.setattr("edge_tts.Communicate", fake_edge_tts.Communicate)

    result = await tts_to_file("Hello streaming", output_path)
    assert result is True


@pytest.mark.asyncio
async def test_tts_to_file_failure(monkeypatch, tmp_path):
    output_path = str(tmp_path / "stream_out.mp3")

    def raise_err(*args, **kwargs):
        raise RuntimeError("Edge-TTS connection failed")

    monkeypatch.setattr("edge_tts.Communicate", raise_err)

    result = await tts_to_file("Hello streaming", output_path)
    assert result is False
