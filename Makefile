# Workflow targets. pyproject.toml is the single source of truth for runtime
# dependencies; the Pipfile installs this project editable so `pipenv lock`
# resolves them from there.

.PHONY: lock install test lint format standings

## Re-resolve dependencies from pyproject.toml and sync the virtualenv.
lock:
	pipenv lock
	pipenv install --dev

## Install the environment from the existing lock file.
install:
	pipenv install --dev

test:
	pipenv run pytest

lint:
	pipenv run ruff check .

format:
	pipenv run ruff format .

## Usage: make standings WEEK=5
standings:
	pipenv run fantasy-standings --week $(WEEK)
