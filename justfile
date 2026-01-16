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
alias p := prod
alias b := build

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

# Build
[group('build')]
[doc("Build web frontend")]
[working-directory('web')]
build:
    bun run build

# Production
[group('prod')]
[doc("Build and serve production server")]
prod: build serve

[group('prod')]
[private]
serve:
    YUBAL_HOST=0.0.0.0 uv run python -m yubal_api

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

# Coverage
[group('test')]
[doc("Run all tests with coverage")]
test-cov: test-cov-py test-cov-web

[group('test')]
[private]
[no-exit-message]
test-cov-py:
    mkdir -p coverage
    uv run pytest packages scripts --cov --cov-report=lcov:coverage/py.lcov

[group('test')]
[private]
[working-directory('web')]
test-cov-web:
    bun test --coverage --coverage-reporter=lcov

# Utils
[group('utils')]
[doc("Generate OpenAPI schema and TypeScript types")]
gen-api:
    @python scripts/generate_openapi.py

# CI
[group('ci')]
[doc("Run all checks (CI)")]
check test_recipe="test": format-check lint typecheck
    just {{ test_recipe }}
    just smoke

[group('ci')]
[doc("Run smoke tests")]
smoke: smoke-py smoke-web

[group('ci')]
[private]
smoke-py:
    uv build --package yubal
    uv build --package yubal-api
    uv run python -c "import yubal_api; print('OK')"

[group('ci')]
[private]
smoke-web: build
    @test -d web/dist && echo "OK"

[group('ci')]
[confirm("Delete all caches?")]
clean:
    rm -rf .pytest_cache .ruff_cache packages/*/.pytest_cache web/dist web/node_modules/.vite dist

# Docker
[group('docker')]
[doc("Build local Docker image")]
docker-build:
    docker build -t yubal:local .

[group('docker')]
[doc("Build image, show size, then remove")]
docker-size:
    @docker build -q -t yubal:size-check . > /dev/null
    @docker images yubal:size-check --format '{{"{{"}}.Size{{"}}"}}'
    @docker rmi yubal:size-check > /dev/null

# yubal CLI
[group('cli')]
cli *args:
    uv run yubal {{ args }}
