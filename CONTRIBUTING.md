# Contributing to VoiceDesk

Thanks for your interest in improving VoiceDesk! This guide covers the basics.

## Development setup

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Frontend
cd frontend && npm install
```

Copy the environment templates and add your keys:

```bash
cp .env.example .env                       # backend (GROQ_API_KEY, etc.)
cp frontend/.env.example frontend/.env.local
```

## Running

```bash
make server     # FastAPI WebSocket server on :8000
make cli        # interactive terminal client
make frontend   # Next.js dev server on :3000
```

## Tests

Run the suite before opening a pull request:

```bash
make test       # or: pytest
```

All new behavior should come with a test. CI runs `pytest` on Python 3.11 and
3.12 for every push and pull request.

## Commit style

This project uses [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`). Keep each commit
focused on a single change.

## Pull requests

1. Branch off `main`.
2. Keep changes small and well-described.
3. Ensure `pytest` passes and no secrets are committed.
