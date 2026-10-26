.PHONY: help install install-dev test server cli frontend clean

help:
	@echo "VoiceDesk - available targets:"
	@echo "  install      Install runtime dependencies"
	@echo "  install-dev  Install runtime + test dependencies"
	@echo "  test         Run the test suite"
	@echo "  server       Start the FastAPI WebSocket server"
	@echo "  cli          Launch the interactive CLI"
	@echo "  frontend     Start the Next.js dev server"
	@echo "  clean        Remove caches and temporary run files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest

server:
	python3 server.py

cli:
	python3 main.py

frontend:
	cd frontend && npm run dev

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache
	rm -f temp_* *.tmp reply.mp3 reply_fast.mp3
