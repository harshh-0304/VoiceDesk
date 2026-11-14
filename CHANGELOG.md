# Changelog

All notable changes to VoiceDesk are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.3.0] - 2026-11-14

### Added
- Multi-service `docker-compose.yml` for unified backend and frontend orchestration.
- Frontend containerization with `frontend/Dockerfile`.
- `GET /api/devices` REST endpoint exposing host audio input hardware to clients.
- `GET /api/stats` and `GET /api/models` system telemetry and model catalog endpoints.
- Client latency estimation with timestamp-echoing in WebSocket heartbeat pings.
- Conversation keyword search `ConversationMemory.search(query)`.
- Markdown conversation transcript export and estimated token consumption metrics.
- High-DPI canvas scaling support for `AudioVisualizer` and `Particles`.
- One-click copy response to clipboard and clear telemetry log actions in UI.
- Comprehensive unit test suites for `groq_client`, `tts`, `tts_stream`, and `audio`.
- GitHub Actions CI workflow adding Next.js frontend lint and build verification.

### Fixed
- Streaming TTS punctuation delimiter splitting to prevent awkward pauses on decimal values and abbreviations.
- Safe audio file deletion helper preventing dangling temporary files.
- PyAudio device enumeration error handling.

## [1.2.0] - 2026-11-02

### Added
- Groq Whisper ASR phantom hallucination suppression on silence.
- Multilingual and configurable speech recognition settings.
- Interactive text query input bar alongside speech streaming.
- Real-time VU mic volume level meter and audio device input selector.
- Portable Windows dev launcher scripts (`run.bat`, `start-backend.bat`, `start-frontend.bat`).

## [1.0.0] - 2026-10-26

### Added
- Initial open-source release of VoiceDesk.
- FastAPI WebSocket duplex audio server.
- Groq Cloud Whisper-large-v3 and LLaMA 3.3 integration.
- Microsoft Edge-TTS neural audio streaming pipeline.
- Next.js reactive frontend dashboard with spectrum audio visualizer.
