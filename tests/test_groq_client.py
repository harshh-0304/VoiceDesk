"""
Unit tests for shared Groq client initialization and caching in VoiceDesk.
"""

from unittest.mock import MagicMock
import utils.groq_client as groq_client_module


def test_missing_groq_api_key_returns_none(monkeypatch):
    monkeypatch.setattr(groq_client_module, "_async_groq_client", None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    client = groq_client_module.get_async_groq_client()
    assert client is None


def test_reset_groq_client(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(groq_client_module, "_async_groq_client", fake_client)
    assert groq_client_module.get_async_groq_client() is fake_client

    groq_client_module.reset_groq_client()
    assert groq_client_module._async_groq_client is None



def test_groq_client_caching(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(groq_client_module, "_async_groq_client", fake_client)

    client1 = groq_client_module.get_async_groq_client()
    client2 = groq_client_module.get_async_groq_client()

    assert client1 is fake_client
    assert client2 is fake_client


def test_groq_client_import_error_handling(monkeypatch):
    monkeypatch.setattr(groq_client_module, "_async_groq_client", None)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_12345")

    import builtins
    orig_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "groq":
            raise ImportError("No module named 'groq'")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    client = groq_client_module.get_async_groq_client()
    assert client is None


def test_reset_groq_client(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(groq_client_module, "_async_groq_client", fake_client)
    assert groq_client_module.get_async_groq_client() is fake_client

    groq_client_module.reset_groq_client()
    assert groq_client_module._async_groq_client is None

