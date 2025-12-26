# Run `just` to see available commands

set dotenv-load

# List available commands
default:
    @just --list

# Run API + frontend dev servers
dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just dev-api &
    just dev-web &
    wait

# Run FastAPI backend with reload
dev-api:
    uv run python -m yubal

# Run Vite frontend
dev-web:
    cd web && bun run dev

# Build both apps
build: build-api build-web

# Build Python package
build-api:
    uv build

# Build frontend for production
build-web:
    cd web && bun run build

# Lint both apps
lint: lint-api lint-web

# Lint Python with ruff
lint-api:
    uv run ruff check .

# Lint frontend with eslint
lint-web:
    cd web && bun run lint

# Format both apps
format: format-api format-web

# Format Python with ruff
format-api:
    uv run ruff format .
    uv run ruff check . --fix

# Format frontend with prettier
format-web:
    cd web && bun run format

# Check formatting without changes
format-check: format-check-api format-check-web

# Check Python formatting
format-check-api:
    uv run ruff format --check .

# Check frontend formatting
format-check-web:
    cd web && bun run format:check

# Generate TypeScript types from OpenAPI
gen-api:
    cd web && bun run generate-api

# Run all checks (lint + format)
check: lint format-check

# Install all dependencies
install: install-api install-web

# Install Python dependencies
install-api:
    uv sync

# Install frontend dependencies
install-web:
    cd web && bun install

# Clean build artifacts
clean:
    rm -rf dist/ .pytest_cache/ .ruff_cache/
    rm -rf web/dist/ web/node_modules/.vite/
