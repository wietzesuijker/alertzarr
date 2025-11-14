PYTHON ?= uv run python

.PHONY: up down logs lint format test clean

up:
	docker compose up -d --wait

logs:
	docker compose logs -f
	down:
	docker compose down -v

lint:
	uv run ruff check src infra

format:
	uv run ruff format src infra

test:
	uv run pytest

clean:
	rm -rf .venv __pycache__ *.egg-info .pytest_cache
