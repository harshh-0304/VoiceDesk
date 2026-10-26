"""
Unit tests for ASR input guards in VoiceDesk.

These exercise the pre-flight validation paths that run before any network
call, so they need no GROQ_API_KEY.
"""

from asr import transcribe_audio_sync


def test_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "does_not_exist.wav"
    assert transcribe_audio_sync(str(missing)) == ""


def test_empty_file_returns_empty(tmp_path):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    assert transcribe_audio_sync(str(empty)) == ""
