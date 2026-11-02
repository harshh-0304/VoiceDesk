"""
Unit tests for ASR input guards and hallucination filtering in VoiceDesk.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from asr import transcribe_audio, transcribe_audio_sync


def test_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "does_not_exist.wav"
    assert transcribe_audio_sync(str(missing)) == ""


def test_empty_file_returns_empty(tmp_path):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    assert transcribe_audio_sync(str(empty)) == ""


@pytest.mark.asyncio
async def test_transcribe_audio_missing_client(monkeypatch, tmp_path):
    monkeypatch.setattr("asr.get_async_groq_client", lambda: None)
    dummy_audio = tmp_path / "sample.wav"
    dummy_audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

    result = await transcribe_audio(str(dummy_audio))
    assert result == ""


@pytest.mark.asyncio
async def test_transcribe_audio_filters_phantom_hallucinations(monkeypatch, tmp_path):
    dummy_audio = tmp_path / "sample.wav"
    dummy_audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

    mock_client = MagicMock()
    monkeypatch.setattr("asr.get_async_groq_client", lambda: mock_client)

    for phantom in [".", "..", "...", "!", "Thank you.", "Thank you", "You", "Bye.", "Silence."]:
        mock_result = MagicMock()
        mock_result.text = phantom
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_result)

        result = await transcribe_audio(str(dummy_audio))
        assert result == "", f"Expected phantom '{phantom}' to be filtered out, got '{result}'"


@pytest.mark.asyncio
async def test_transcribe_audio_success(monkeypatch, tmp_path):
    dummy_audio = tmp_path / "sample.wav"
    dummy_audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

    mock_client = MagicMock()
    monkeypatch.setattr("asr.get_async_groq_client", lambda: mock_client)

    mock_result = MagicMock()
    mock_result.text = "Hello VoiceDesk, can you help me today?"
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_result)

    result = await transcribe_audio(str(dummy_audio))
    assert result == "Hello VoiceDesk, can you help me today?"
