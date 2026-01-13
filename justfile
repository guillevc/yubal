set dotenv-load

# Project root directory (can be overridden via .env or env var)
export YUBAL_ROOT := justfile_directory()

default:
    @just --list

install:
    uv sync
    cd web && bun install

cli *args:
    uv run yubal {{ args }}

dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just dev-api & just dev-web & wait

dev-api:
    uv run uvicorn yubal_api.api.app:app --reload

dev-web:
    cd web && bun run dev

lint:
    uv run ruff check packages

lint-fix:
    uv run ruff check packages --fix

format:
    uv run ruff format packages

typecheck:
    uv run ty check packages

test *args:
    uv run pytest {{ args }}

check: lint typecheck test
