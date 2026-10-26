# Changelog

All notable changes to VoiceDesk are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- MIT `LICENSE`.
- `requirements-dev.txt` for test and CLI extras.
- `pytest.ini` so bare `pytest` resolves imports from the repo root.
- `Makefile`, `.editorconfig`, `.gitattributes`, and `.dockerignore`.
- Backend `Dockerfile` (includes ffmpeg for TTS speed adjustment).
- GitHub Actions CI running the test suite on Python 3.11 and 3.12.
- `MAX_AUDIO_BYTES` guard rejecting oversized WebSocket audio payloads.
- Role validation in `ConversationMemory`.
- Added tests for ASR guards, memory validation, and WebSocket handling.

### Fixed
- `is_microphone_available()` now enumerates input devices by global index.
- TTS playback speed is clamped to ffmpeg's supported `atempo` range (0.5–2.0).
- `ConversationMemory.from_dict` skips malformed/unknown-role entries.

### Changed
- Removed generated audio artifacts and a stray screenshot from version control.
- Moved development dependencies out of the runtime `requirements.txt`.
