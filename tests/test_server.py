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


def test_api_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "version" in data
    assert "active_model" in data
    assert "active_voice" in data
    assert "max_audio_bytes" in data


def test_api_models_endpoint():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "llm_models" in data
    assert "asr_models" in data
    assert len(data["llm_models"]) >= 2
    assert any(m["id"] == "llama-3.3-70b-versatile" for m in data["llm_models"])
    assert any(m["id"] == "whisper-large-v3" for m in data["asr_models"])


def test_api_devices_endpoint(monkeypatch):
    monkeypatch.setattr("server.get_audio_input_devices", lambda: [{"index": 0, "name": "Mock Mic", "channels": 1}])
    response = client.get("/api/devices")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["devices"][0]["name"] == "Mock Mic"


def test_load_system_prompt():
    prompt = load_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_websocket_ping_pong():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "ping"})
        reply = ws.receive_json()
        assert reply["type"] == "pong"
        assert "server_time" in reply


def test_websocket_ping_timestamp_echo():
    with client.websocket_connect("/ws/audio") as ws:
        ts = 1731590000.123
        ws.send_json({"type": "ping", "timestamp": ts})
        reply = ws.receive_json()
        assert reply["type"] == "pong"
        assert reply["client_timestamp"] == ts
        assert "server_time" in reply


def test_websocket_rejects_invalid_json():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_text("not-json")
        reply = ws.receive_json()
        assert reply["type"] == "error"


def test_websocket_clear_memory():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "clear_memory"})
        reply = ws.receive_json()
        assert reply == {"type": "memory_cleared"}


def test_websocket_commit_missing_audio():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "commit"})
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert "Missing audio_data" in reply["message"]


def test_websocket_commit_invalid_base64():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "commit", "audio_data": "!!!not_base64!!!"})
        reply = ws.receive_json()
        assert reply["type"] == "error"


def test_websocket_text_query_empty():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "text_query", "text": "   "})
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert "Empty text prompt" in reply["message"]


def test_websocket_text_query_success(monkeypatch):
    async def mock_generate_stream(*args, **kwargs):
        yield "Hello "
        yield "world!"

    async def mock_audio_stream(text_iter):
        async for _ in text_iter:
            pass
        yield b"fake_mp3_chunk"

    monkeypatch.setattr("server.generate_response_stream", mock_generate_stream)
    monkeypatch.setattr("server.generate_audio_stream", mock_audio_stream)

    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "text_query", "text": "Hi there"})

        # 1. User transcription echo
        m1 = ws.receive_json()
        assert m1["type"] == "transcription"
        assert m1["text"] == "Hi there"

        # 2. Speaking status
        m2 = ws.receive_json()
        assert m2["type"] == "status"
        assert m2["state"] == "speaking"

        # 3. Text deltas & audio chunks
        received_types = []
        full_text = ""
        while True:
            msg = ws.receive_json()
            received_types.append(msg["type"])
            if msg["type"] == "text_delta":
                full_text += msg["delta"]
            elif msg["type"] == "status" and msg["state"] == "listening":
                break

        assert "text_delta" in received_types
        assert "audio_stream" in received_types
        assert "response_complete" in received_types
        assert full_text == "Hello world!"

