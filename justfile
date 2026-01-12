default:
    @just --list

# Run the CLI
run *args:
    uv run ytmeta {{ args }}

# Install dependencies
install:
    uv sync

# Format code
format:
    uv run ruff format ytmeta

# Check formatting
format-check:
    uv run ruff format --check ytmeta

# Lint code
lint:
    uv run ruff check ytmeta

# Lint and fix
lint-fix:
    uv run ruff check --fix ytmeta

# Type check
typecheck:
    uv run ty check ytmeta

# Run tests
test *args:
    uv run pytest {{ args }}

# Run all checks
check: format-check lint typecheck test
