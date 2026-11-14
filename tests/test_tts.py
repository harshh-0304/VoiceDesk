"""
Unit tests for file-based TTS engine in VoiceDesk.
"""

from unittest.mock import MagicMock
import os
import pytest
from tts import text_to_speech


def test_tts_empty_string_returns_none():
    assert text_to_speech("") is None
    assert text_to_speech("   ") is None


def test_tts_missing_gtts_returns_none(monkeypatch):
    import builtins
    orig_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "gtts":
            raise ImportError("gTTS missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    assert text_to_speech("Hello world") is None


def test_tts_success_without_ffmpeg(monkeypatch, tmp_path):
    output_file = str(tmp_path / "speech.mp3")

    fake_gtts_instance = MagicMock()
    def fake_save(path):
        with open(path, "wb") as f:
            f.write(b"fake_mp3_content")
    fake_gtts_instance.save.side_effect = fake_save

    fake_gtts_cls = MagicMock(return_value=fake_gtts_instance)

    monkeypatch.setattr("shutil.which", lambda bin_name: None)
    monkeypatch.setattr("gtts.gTTS", fake_gtts_cls)

    result = text_to_speech("Testing voice desk", output_path=output_file, speed=1.0)
    assert result == output_file
    assert os.path.exists(output_file)
    assert open(output_file, "rb").read() == b"fake_mp3_content"


def test_cleanup_audio_file(tmp_path):
    from tts import cleanup_audio_file

    sample = tmp_path / "delete_me.mp3"
    sample.write_bytes(b"data")
    assert sample.exists()

    assert cleanup_audio_file(str(sample)) is True
    assert not sample.exists()
    assert cleanup_audio_file(str(sample)) is False
    assert cleanup_audio_file(None) is False

