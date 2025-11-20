PYTHON ?= uv run python

.PHONY: up down logs lint format test clean titiler

up:
	docker compose up -d --wait

down:
	docker compose down -v

logs:
	docker compose logs -f

lint:
	uv run ruff check src

format:
	uv run ruff format src

test:
	uv run pytest

clean:
	rm -rf .venv __pycache__ *.egg-info .pytest_cache

titiler:
	TITILER_BASE_URL=http://127.0.0.1:8080 docker compose up -d titiler --wait
