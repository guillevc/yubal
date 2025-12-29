set dotenv-load

default:
    @just --list

# Aliases
alias c := check
alias f := format
alias l := lint
alias t := typecheck
alias d := dev
alias b := build-web
alias i := install
alias p := prod

# Dev
dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just dev-api & just dev-web & wait

dev-api:
    YUBAL_RELOAD=true YUBAL_DEBUG=true uv run python -m yubal

dev-web:
    cd web && bun run dev

# Production
prod: build-web serve

serve:
    YUBAL_HOST=0.0.0.0 uv run python -m yubal

# Build
build: build-web
build-web:
    cd web && bun run build

# Docker
build-docker:
    docker build -t yubal .

# Lint
lint: lint-api lint-web
lint-api:
    uv run ruff check .
lint-web:
    cd web && bun run lint

# Typecheck
typecheck: typecheck-api typecheck-web
typecheck-api:
    uv run ty check
typecheck-web:
    cd web && bun run typecheck

# Format
format: format-api format-web
format-api:
    uv run ruff format .
    uv run ruff check --fix .
format-web:
    cd web && bun run format

format-check: format-check-api format-check-web
format-check-api:
    uv run ruff format --check .
format-check-web:
    cd web && bun run format:check

# Tests
test:
    uv run pytest
test-cov:
    uv run pytest --cov

# Utils
gen-api:
    cd web && bun run generate-api
dead-exclusions:
    uv run dead --exclude '^yubal/(api|schemas)/.*'

check: lint format-check typecheck test

install: install-api install-web
install-api:
    uv sync
install-web:
    cd web && bun install

clean:
    rm -rf dist/ .pytest_cache/ .ruff_cache/ web/dist/ web/node_modules/.vite/
