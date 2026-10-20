"""
Unit tests for FastAPI endpoints in VoiceDesk.
"""

from fastapi.testclient import TestClient
from server import app, load_system_prompt

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "VoiceDesk"
    assert "endpoints" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "default_model" in data
    assert "default_voice" in data


def test_api_info_endpoint():
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VoiceDesk Real-Time Voice Engine"
    assert data["sample_rate"] == 16000
    assert data["format"] == "audio/wav"


def test_load_system_prompt():
    prompt = load_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0
