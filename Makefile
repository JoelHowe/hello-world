.PHONY: help install install-backend install-frontend dev backend frontend test ingest clean

help:
	@echo "make install        - install backend and frontend deps"
	@echo "make dev            - run backend (:8000) and frontend (:5173) together"
	@echo "make backend        - run just the FastAPI backend"
	@echo "make frontend       - run just the Vite dev server"
	@echo "make test           - run backend pytest suite"
	@echo "make ingest         - run a one-shot ingestion from the CLI"
	@echo "make clean          - remove build artifacts and caches"

install: install-backend install-frontend

install-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'

install-frontend:
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Runs backend and frontend in parallel. Ctrl-C kills both.
dev:
	@$(MAKE) -j2 backend frontend

test:
	cd backend && . .venv/bin/activate && pytest -q

ingest:
	cd backend && . .venv/bin/activate && python -m app.cli ingest

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
	rm -rf frontend/dist frontend/.vite
