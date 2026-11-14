"""
Unit tests for audio capture utilities in VoiceDesk.
"""

from unittest.mock import MagicMock
from utils.audio import get_audio_input_devices, is_microphone_available, record_microphone


def test_microphone_available_pyaudio_missing(monkeypatch):
    import builtins
    orig_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pyaudio":
            raise ImportError("PyAudio missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    assert is_microphone_available() is False


def test_microphone_available_with_devices(monkeypatch):
    fake_pa = MagicMock()
    fake_pa.get_device_count.return_value = 2
    fake_pa.get_device_info_by_index.side_effect = [
        {"maxInputChannels": 0, "name": "Output Speaker"},
        {"maxInputChannels": 1, "name": "Built-in Mic"},
    ]

    fake_pyaudio_mod = MagicMock()
    fake_pyaudio_mod.PyAudio.return_value = fake_pa

    import sys
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio_mod)

    assert is_microphone_available() is True
    fake_pa.terminate.assert_called_once()


def test_microphone_available_no_input_devices(monkeypatch):
    fake_pa = MagicMock()
    fake_pa.get_device_count.return_value = 1
    fake_pa.get_device_info_by_index.return_value = {"maxInputChannels": 0, "name": "Headphones"}

    fake_pyaudio_mod = MagicMock()
    fake_pyaudio_mod.PyAudio.return_value = fake_pa

    import sys
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio_mod)

    assert is_microphone_available() is False
    fake_pa.terminate.assert_called_once()


def test_record_microphone_missing_pyaudio(monkeypatch):
    import builtins
    orig_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pyaudio":
            raise ImportError("PyAudio missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    assert record_microphone() is None


def test_get_audio_input_devices(monkeypatch):
    fake_pa = MagicMock()
    fake_pa.get_device_count.return_value = 2
    fake_pa.get_device_info_by_index.side_effect = [
        {"maxInputChannels": 0, "name": "Speakers"},
        {"maxInputChannels": 2, "name": "USB Mic", "defaultSampleRate": 44100},
    ]

    fake_pyaudio_mod = MagicMock()
    fake_pyaudio_mod.PyAudio.return_value = fake_pa

    import sys
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio_mod)

    devs = get_audio_input_devices()
    assert len(devs) == 1
    assert devs[0]["name"] == "USB Mic"
    assert devs[0]["channels"] == 2
    assert devs[0]["default_sample_rate"] == 44100
    fake_pa.terminate.assert_called_once()

