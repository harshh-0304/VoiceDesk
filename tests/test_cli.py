"""
Unit tests for CLI helper utilities in VoiceDesk.
"""

from unittest.mock import MagicMock
from main import load_system_prompt, play_audio_file


def test_cli_load_system_prompt_fallback(tmp_path):
    missing_file = str(tmp_path / "non_existent.txt")
    prompt = load_system_prompt(missing_file)
    assert isinstance(prompt, str)
    assert "VoiceDesk" in prompt


def test_cli_load_system_prompt_custom(tmp_path):
    custom = tmp_path / "custom_prompt.txt"
    custom.write_text("You are an assistant for unit testing.", encoding="utf-8")

    prompt = load_system_prompt(str(custom))
    assert prompt == "You are an assistant for unit testing."


def test_cli_play_audio_missing_file_safe():
    # Should not raise exception
    play_audio_file("")
    play_audio_file("non_existent_audio_file.mp3")


def test_cli_play_audio_player_dispatch(monkeypatch, tmp_path):
    fake_audio = tmp_path / "sound.mp3"
    fake_audio.write_bytes(b"data")

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}" if name == "ffplay" else None)

    play_audio_file(str(fake_audio))
    mock_run.assert_called_once()
