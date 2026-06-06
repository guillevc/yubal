set dotenv-load

# Project root directory (can be overridden via .env or env var)
export YUBAL_ROOT := justfile_directory()

export GITHUB_TOKEN := env("GITHUB_TOKEN", `gh auth token 2>/dev/null || true`)

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
alias doc := docs-serve

# Browser extension
mod ext 'extension'

# Install (frozen lockfiles for CI)
[doc("Install all dependencies (frozen)")]
[group('setup')]
install: install-py install-web

[group('setup')]
[private]
install-py:
    uv sync --frozen --all-packages --all-extras

[group('setup')]
[private]
[working-directory('web')]
install-web:
    bun install --frozen-lockfile

# Sync (for development)
[doc("Sync dependencies (updates lockfile)")]
[group('setup')]
sync: sync-py sync-web

[group('setup')]
[private]
sync-py:
    uv sync --all-packages --all-extras

[group('setup')]
[private]
[working-directory('web')]
sync-web:
    bun install

# Upgrade
[doc("Upgrade all dependencies")]
[group('setup')]
upgrade: upgrade-py upgrade-web

[group('setup')]
[private]
upgrade-py:
    uv lock --upgrade && uv sync --all-packages

[group('setup')]
[private]
[working-directory('web')]
upgrade-web:
    bun update

[doc("Upgrade all deps to latest")]
[group('setup')]
upgrade-yolo: upgrade-yolo-py upgrade-yolo-web

[group('setup')]
[private]
[working-directory('web')]
upgrade-yolo-web:
    bunx npm-check-updates -u
    bun install

[group('setup')]
[private]
upgrade-yolo-py:
    uv lock --upgrade
    uv sync --all-packages
    @echo ""
    @echo "📦 Outdated (constraints may be blocking):"
    @uv pip list --outdated || true

# Dev
[doc("Run API + Web dev servers")]
[group('dev')]
[script('bash')]
dev:
    trap 'kill 0' EXIT
    just dev-api & just dev-web & wait

[group('dev')]
[private]
dev-api:
    YUBAL_LOG_LEVEL=DEBUG uv run uvicorn yubal_api.api.app:app --reload

[group('dev')]
[private]
[working-directory('web')]
dev-web:
    bun --bun run dev

# Build
[doc("Build web frontend")]
[group('build')]
[working-directory('web')]
build:
    bun --bun run build

# Production
[doc("Build and serve production server")]
[group('prod')]
prod: build serve

[group('prod')]
[private]
serve:
    YUBAL_HOST=0.0.0.0 uv run python -m yubal_api

# Lint
[doc("Lint Python + Web")]
[group('lint')]
lint: lint-py lint-web

[group('lint')]
[private]
lint-py:
    uv run ruff check packages scripts

[group('lint')]
[private]
[working-directory('web')]
lint-web:
    bun --bun run lint

# Lint fix
[doc("Lint and fix Python + Web")]
[group('lint')]
lint-fix: lint-fix-py lint-fix-web

[group('lint')]
[private]
lint-fix-py:
    uv run ruff check packages scripts --fix

[group('lint')]
[private]
[working-directory('web')]
lint-fix-web:
    bun --bun run lint --fix

# Format
[doc("Format Python + Web + Root files")]
[group('format')]
format: format-py format-web format-root

[group('format')]
[private]
format-py:
    uv run ruff format packages scripts

[group('format')]
[private]
[working-directory('web')]
format-web:
    bun --bun run format

[group('format')]
[private]
format-root:
    bunx --bun prettier --write "*.md" "*.yaml" --ignore-unknown

# Format check
[doc("Check formatting Python + Web + Root files")]
[group('format')]
format-check: format-check-py format-check-web format-check-root

[group('format')]
[private]
format-check-py:
    uv run ruff format --check packages scripts

[group('format')]
[private]
[working-directory('web')]
format-check-web:
    bun --bun run format:check

[group('format')]
[private]
format-check-root:
    bunx --bun prettier --check "*.md" "*.yaml" --ignore-unknown

# Typecheck
[doc("Typecheck Python + Web")]
[group('typecheck')]
typecheck: typecheck-py typecheck-web

[group('typecheck')]
[private]
typecheck-py:
    uv run ty check packages scripts

[group('typecheck')]
[private]
[working-directory('web')]
typecheck-web:
    bun --bun run typecheck

# Tests
[doc("Run all tests")]
[group('test')]
test: test-py test-web

[group('test')]
[no-exit-message]
[private]
test-py:
    uv run pytest packages scripts

[group('test')]
[private]
[working-directory('web')]
test-web:
    bun --bun run test

# E2E
[doc("Run Playwright e2e tests")]
[group('test')]
[working-directory('e2e')]
test-e2e: build
    bun install && bun run install-browsers && bun run test

# Coverage
[doc("Run all tests with coverage")]
[group('test')]
test-cov: test-cov-py test-cov-web

[group('test')]
[no-exit-message]
[private]
test-cov-py:
    mkdir -p coverage
    uv run pytest packages scripts --cov --cov-report=lcov:coverage/py.lcov

[group('test')]
[private]
[working-directory('web')]
test-cov-web:
    bun test --coverage --coverage-reporter=lcov

# Utils
[doc("Generate OpenAPI schema and TypeScript types")]
[group('utils')]
gen-api:
    @python scripts/generate_openapi.py

[confirm]
[doc("Bump version across all packages")]
[group('utils')]
[script('bash')]
version VERSION:
    set -euo pipefail

    # Update Python packages
    uv version --frozen --package yubal {{ VERSION }}
    uv version --frozen --package yubal-api {{ VERSION }}
    uv version --frozen {{ VERSION }}

    # Update web package
    (cd web && npm pkg set version={{ VERSION }})

    # Sync lockfiles
    just sync

    # Commit and tag
    git add pyproject.toml packages/*/pyproject.toml uv.lock web/package.json web/bun.lock
    git diff --cached --quiet || git commit -m "chore: bump version to {{ VERSION }}"
    git tag v{{ VERSION }}

[doc("Preview changelog from a ref to HEAD or another ref")]
[group('utils')]
changelog from to="HEAD":
    git cliff {{ from }}..{{ to }}

[doc("Write full changelog to CHANGELOG.md")]
[group('utils')]
changelog-md:
    git cliff --output CHANGELOG.md

# CI
[doc("Run all checks (CI)")]
[group('ci')]
check test_recipe="test": format-check lint typecheck
    just {{ test_recipe }}
    just smoke

[doc("Run smoke tests")]
[group('ci')]
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

[confirm("Delete all caches?")]
[group('ci')]
clean:
    rm -rf .pytest_cache .ruff_cache packages/*/.pytest_cache web/dist web/node_modules/.vite dist

# Docker
[doc("Build local Docker image")]
[group('docker')]
docker-build:
    docker build -t yubal:local .

[doc("Build image, show size, then remove")]
[group('docker')]
docker-size:
    docker build -t yubal:docker-size .
    @docker images yubal:docker-size --format '{{ "{{" }}.Size{{ "}}" }}'
    @docker rmi yubal:docker-size

[doc("Run docker compose up")]
[group('docker')]
compose *args:
    docker compose up --build {{ args }}

[doc("Lint Dockerfile")]
[group('lint')]
docker-lint:
    @docker run --rm -i hadolint/hadolint < Dockerfile

[doc("Detect dead code")]
[group('lint')]
dead-code: dead-code-py dead-code-web

[doc("Detect dead Python code")]
[group('lint')]
dead-code-py:
    uv run --with vulture vulture packages/yubal/src packages/api/src scripts --min-confidence 60

[doc("Detect dead web code")]
[group('lint')]
[working-directory('web')]
dead-code-web:
    bunx --bun knip

# Documentation
[doc("Generate API documentation")]
[group('docs')]
docs:
    uv run --with pdoc pdoc yubal --output-dir docs/pdoc/yubal --docformat google

[doc("Serve API documentation locally")]
[group('docs')]
docs-serve:
    uv run --with pdoc pdoc yubal --docformat google

# yubal CLI
[group('cli')]
[positional-arguments]
cli *args:
    uv run yubal "$@"

# Database migrations
[doc("Generate a new migration")]
[group('db')]
[working-directory('packages/api/src/yubal_api')]
db-generate message:
    uv run alembic revision --autogenerate -m "{{ message }}"

[doc("Run pending migrations")]
[group('db')]
[working-directory('packages/api/src/yubal_api')]
db-migrate:
    uv run alembic upgrade head

[confirm("Delete database and run all migrations?")]
[doc("Reset database (delete and recreate)")]
[group('db')]
[working-directory('packages/api/src/yubal_api')]
db-reset:
    rm -f "${YUBAL_CONFIG:-config}/yubal/yubal.db"
    uv run alembic upgrade head

[confirm("Delete all migrations and regenerate from current schema?")]
[doc("Consolidate all migrations into a single initial migration")]
[group('db')]
[working-directory('packages/api/src/yubal_api')]
db-consolidate:
    rm -f "${YUBAL_CONFIG:-config}/yubal/yubal.db"
    rm -f migrations/versions/*.py
    uv run alembic revision --autogenerate -m "Initial schema"
    uv run alembic upgrade head
