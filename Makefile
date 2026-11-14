.PHONY: help install install-dev test lint-frontend build-frontend server cli frontend docker-up docker-down clean

help:
	@echo "VoiceDesk - available targets:"
	@echo "  install        Install runtime dependencies"
	@echo "  install-dev    Install runtime + test dependencies"
	@echo "  test           Run Python unit tests"
	@echo "  lint-frontend  Run ESLint check on Next.js frontend"
	@echo "  build-frontend Build Next.js production bundle"
	@echo "  server         Start the FastAPI WebSocket server"
	@echo "  cli            Launch the interactive CLI"
	@echo "  frontend       Start the Next.js dev server"
	@echo "  docker-up      Start backend and frontend with Docker Compose"
	@echo "  docker-down    Stop Docker Compose containers"
	@echo "  clean          Remove caches and temporary run files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest

lint-frontend:
	npm --prefix frontend run lint

build-frontend:
	npm --prefix frontend run build

server:
	python3 server.py

cli:
	python3 main.py

frontend:
	cd frontend && npm run dev

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache
	rm -f temp_* *.tmp reply.mp3 reply_fast.mp3 debug_last_audio*
