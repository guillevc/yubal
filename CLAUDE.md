# CLAUDE.md

## Rules

- Run `just format` after changing code
- Prompt user to run `just check` and fix all errors after major changes
- No backwards compatibility—break freely, update all dependent code
- Use expert language subagents for specialized tasks
- Never prompt to commit or push unless explicitly requested

## Just Commands

Available commands via `just`. Use these instead of raw tool commands.

| Command           | Description                    |
| ----------------- | ------------------------------ |
| `build`           | Build web frontend             |
| `check`           | Run all checks (CI)            |
| `clean`           | Clean build artifacts          |
| `smoke`           | Run smoke tests                |
| `cli *args`       | yubal CLI                      |
| `dev`             | Run API + Web dev servers      |
| `compose *args`   | Run docker compose             |
| `docker-build`    | Build local Docker image       |
| `docker-size`     | Build image, show size, remove |
| `docs`            | Generate API documentation     |
| `docs-serve`      | Serve API docs locally         |
| `format`          | Format Python + Web + Root     |
| `format-check`    | Check formatting               |
| `docker-lint`     | Lint Dockerfile                |
| `lint`            | Lint Python + Web              |
| `lint-fix`        | Lint and fix                   |
| `prod`            | Build and serve production     |
| `install`         | Install deps (frozen)          |
| `sync`            | Sync deps (updates lockfile)   |
| `upgrade`         | Upgrade all deps               |
| `upgrade-yolo`    | Upgrade all to latest          |
| `test`            | Run all tests                  |
| `test-cov`        | Run tests with coverage        |
| `typecheck`       | Typecheck Python + Web         |
| `gen-api`         | Generate OpenAPI + TS types    |
| `version VERSION` | Bump version                   |
