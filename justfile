set dotenv-load

# Project root directory (can be overridden via .env or env var)
export YUBAL_ROOT := justfile_directory()

default:
    @just --list

# Aliases
alias i := install
alias d := dev
alias l := lint
alias f := format
alias t := test
alias c := check

# Install
[group('setup')]
[doc("Install all dependencies")]
install: install-py install-web

[group('setup')]
[private]
install-py:
    uv sync --all-packages

[group('setup')]
[private]
[working-directory('web')]
install-web:
    bun install

# Dev
[group('dev')]
[doc("Run API + Web dev servers")]
[script('bash')]
dev:
    trap 'kill 0' EXIT
    just dev-api & just dev-web & wait

[group('dev')]
[private]
dev-api:
    uv run uvicorn yubal_api.api.app:app --reload

[group('dev')]
[private]
[working-directory('web')]
dev-web:
    bun run dev

# Lint
[group('lint')]
[doc("Lint Python + Web")]
lint: lint-py lint-web

[group('lint')]
[private]
lint-py:
    uv run ruff check packages scripts

[group('lint')]
[private]
[working-directory('web')]
lint-web:
    bun run lint

# Lint fix
[group('lint')]
[doc("Lint and fix Python + Web")]
lint-fix: lint-fix-py lint-fix-web

[group('lint')]
[private]
lint-fix-py:
    uv run ruff check packages scripts --fix

[group('lint')]
[private]
[working-directory('web')]
lint-fix-web:
    bun run lint --fix

# Format
[group('format')]
[doc("Format Python + Web")]
format: format-py format-web

[group('format')]
[private]
format-py:
    uv run ruff format packages scripts

[group('format')]
[private]
[working-directory('web')]
format-web:
    bun run format

# Format check
[group('format')]
[doc("Check formatting Python + Web")]
format-check: format-check-py format-check-web

[group('format')]
[private]
format-check-py:
    uv run ruff format --check packages scripts

[group('format')]
[private]
[working-directory('web')]
format-check-web:
    bun run format:check

# Typecheck
[group('typecheck')]
[doc("Typecheck Python + Web")]
typecheck: typecheck-py typecheck-web

[group('typecheck')]
[private]
typecheck-py:
    uv run ty check packages scripts

[group('typecheck')]
[private]
[working-directory('web')]
typecheck-web:
    bun run typecheck

# Tests
[group('test')]
[doc("Run all tests")]
test: test-py test-web

[group('test')]
[private]
[no-exit-message]
test-py:
    uv run pytest packages scripts

[group('test')]
[private]
[working-directory('web')]
test-web:
    bun run test

# Utils
[group('utils')]
[doc("Generate OpenAPI schema and TypeScript types")]
gen-api:
    @python scripts/generate_openapi.py

# CI
[group('ci')]
[doc("Run all checks (CI)")]
check: format-check lint typecheck test

[group('ci')]
[confirm("Delete all caches?")]
clean:
    rm -rf .pytest_cache .ruff_cache packages/*/.pytest_cache web/dist web/node_modules/.vite

# Docker
[group('docker')]
docker-build:
    docker build --no-cache -t yubal:local .

[group('docker')]
docker-check-size:
    docker build --no-cache -t yubal:check-size .
    docker images yubal:check-size | awk 'NR==2 {print "📦 Image size: " $7}'
    docker rmi yubal:check-size
    @echo '✅ Docker build successful!'

# yubal CLI
[group('cli')]
cli *args:
    uv run yubal {{ args }}
