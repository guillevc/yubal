# CLAUDE.md

## Rules

- Run `just format` and `just lint-fix` after changing code.
- Prompt user to run `just check` and fix all errors after major changes.
- No backwards compatibility. Break freely, update all dependent code.
- Use expert language subagents for specialized tasks.
- Never prompt to commit or push unless explicitly requested.
- Use Context7 MCP to fetch documentation.

## Just Commands

Available commands via `just`. Use these instead of raw tool commands.

```
Available recipes:
    default

    [build]
    build                    # Build web frontend [alias: b]

    [ci]
    check test_recipe="test" # Run all checks (CI) [alias: c]
    clean
    smoke                    # Run smoke tests

    [cli]
    cli *args                # yubal CLI

    [dev]
    dev                      # Run API + Web dev servers [alias: d]

    [docker]
    compose *args            # Run docker compose up
    docker-build             # Build local Docker image
    docker-size              # Build image, show size, then remove

    [docs]
    docs                     # Generate API documentation
    docs-serve               # Serve API documentation locally [alias: doc]

    [format]
    format                   # Format Python + Web + Root files [alias: f]
    format-check             # Check formatting Python + Web + Root files

    [lint]
    dead-code                # Detect dead Python code
    docker-lint              # Lint Dockerfile
    lint                     # Lint Python + Web [alias: l]
    lint-fix                 # Lint and fix Python + Web

    [prod]
    prod                     # Build and serve production server [alias: p]

    [setup]
    install                  # Install all dependencies (frozen) [alias: i]
    sync                     # Sync dependencies (updates lockfile)
    upgrade                  # Upgrade all dependencies
    upgrade-yolo             # Upgrade all deps to latest

    [test]
    test                     # Run all tests [alias: t]
    test-cov                 # Run all tests with coverage

    [typecheck]
    typecheck                # Typecheck Python + Web

    [utils]
    gen-api                  # Generate OpenAPI schema and TypeScript types
    version VERSION          # Bump version across all packages
```
