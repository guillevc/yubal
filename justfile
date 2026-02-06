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
alias doc := docs-serve

# Install (frozen lockfiles for CI)
[group('setup')]
[doc("Install all dependencies (frozen)")]
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
[group('setup')]
[doc("Sync dependencies (updates lockfile)")]
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
[group('setup')]
[doc("Upgrade all dependencies")]
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

[group('setup')]
[doc("Upgrade all deps to latest")]
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
[group('dev')]
[doc("Run API + Web dev servers")]
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
[doc("Format Python + Web + Root files")]
format: format-py format-web format-root

[group('format')]
[private]
format-py:
    uv run ruff format packages scripts

[group('format')]
[private]
[working-directory('web')]
format-web:
    bun run format

[group('format')]
[private]
format-root:
    bunx prettier --write "*.md" "*.yaml" --ignore-unknown

# Format check
[group('format')]
[doc("Check formatting Python + Web + Root files")]
format-check: format-check-py format-check-web format-check-root

[group('format')]
[private]
format-check-py:
    uv run ruff format --check packages scripts

[group('format')]
[private]
[working-directory('web')]
format-check-web:
    bun run format:check

[group('format')]
[private]
format-check-root:
    bunx prettier --check "*.md" "*.yaml" --ignore-unknown

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
[doc("Bump version across all packages")]
[confirm]
[script('bash')]
version VERSION:
    set -euo pipefail

    # Update Python packages
    find . -name "pyproject.toml" -not -path "./.*" \
        -exec sed -i '' 's/^version = ".*"/version = "{{VERSION}}"/' {} \;

    # Update web package
    (cd web && npm pkg set version={{VERSION}})

    # Sync lockfiles
    just sync

    # Commit and tag
    git add pyproject.toml packages/*/pyproject.toml uv.lock web/package.json web/bun.lock
    git commit -m "chore: bump version to {{VERSION}}"
    git tag v{{VERSION}}

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
    docker build -t yubal:docker-size .
    @docker images yubal:docker-size --format '{{"{{"}}.Size{{"}}"}}'
    @docker rmi yubal:docker-size

[group('docker')]
[doc("Run docker compose up")]
compose *args:
    docker compose up --build {{ args }}

[group('lint')]
[doc("Lint Dockerfile")]
docker-lint:
    @docker run --rm -i hadolint/hadolint < Dockerfile

[group('lint')]
[doc("Detect dead Python code")]
dead-code: dead-code-py dead-code-web

[group('lint')]
[private]
dead-code-py:
    uv run --with vulture vulture packages/yubal/src packages/api/src scripts --min-confidence 80

[group('lint')]
[private]
[working-directory('web')]
dead-code-web:
    bunx knip

# Documentation
[group('docs')]
[doc("Generate API documentation")]
docs:
    uv run --with pdoc pdoc yubal --output-dir docs/pdoc/yubal --docformat google

[group('docs')]
[doc("Serve API documentation locally")]
docs-serve:
    uv run --with pdoc pdoc yubal --docformat google

# yubal CLI
[group('cli')]
[positional-arguments]
cli *args:
    uv run yubal "$@"

# Database migrations
[group('db')]
[doc("Generate a new migration")]
[working-directory('packages/api/src/yubal_api')]
db-generate message:
    uv run alembic revision --autogenerate -m "{{message}}"

[group('db')]
[doc("Run pending migrations")]
[working-directory('packages/api/src/yubal_api')]
db-migrate:
    uv run alembic upgrade head

[group('db')]
[doc("Reset database (delete and recreate)")]
[working-directory('packages/api/src/yubal_api')]
[confirm("Delete database and run all migrations?")]
db-reset:
    rm -f "${YUBAL_CONFIG:-config}/yubal/yubal.db"
    uv run alembic upgrade head

[group('db')]
[doc("Consolidate all migrations into a single initial migration")]
[working-directory('packages/api/src/yubal_api')]
[confirm("Delete all migrations and regenerate from current schema?")]
db-consolidate:
    rm -f "${YUBAL_CONFIG:-config}/yubal/yubal.db"
    rm -f migrations/versions/*.py
    uv run alembic revision --autogenerate -m "Initial schema"
    uv run alembic upgrade head
