.PHONY: setup fmt check test

setup:
	uv sync --all-groups

fmt:
	uv run ruff format .
	uv run ruff check --fix .

check:
	uv run ruff check .
	uv run mypy src apps tests
	uv run pytest

test:
	uv run pytest