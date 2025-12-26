# CLAUDE.md

## API guidelines

- Run `just gen-api` (from project root) if there have been API changes.
- Jobs
  - Support job queuing and in-memory persistance of jobs.
  - We always want to run one job at a time, sequentially. Avoid multiple youtube downloads and beet imports at the same time.
  - Executing a job should download from yt-dlp and then process with beets.

## Web app guidelines

- Use components from @heroui/react.
- HeroUI v2 docs: https://www.heroui.com/docs
- Prefer using HeroUI component variants to customize HeroUI components.
- Use HeroUI-defined semantic colors always when overriding HeroUI or custom components.
- Make use of tailwindcss.
- Prefer defining single-file components.
- Use openapi-fetch with the generated schemas from FastAPI.

### HeroUI Semantic colors and variables
#### Text
```
text-foreground        # Primary text
text-foreground-500    # Muted text
text-foreground-400    # Faint text (hints, timestamps)
text-primary           # Links, interactive
text-success           # Success messages
text-warning           # Warnings
text-danger            # Errors
```

#### Backgrounds
```
bg-background          # Page background
bg-content1            # Cards, modals
bg-content2            # Nested sections
bg-content3            # Deeper nesting (code blocks)
bg-content4            # Deepest nesting
bg-default-100         # Input backgrounds
bg-default-50          # Subtle hover states
```

#### Borders
```
border-default-200     # Default borders (inputs, cards)
border-default-300     # Stronger borders
border-divider         # Dividers
border-primary         # Active/focus states
```

#### Semantic Colors
| Color     | Use                        |
|-----------|----------------------------|
| primary   | Links, buttons, focus      |
| secondary | Alternative accents        |
| success   | Success states, checkmarks |
| warning   | Warnings, caution          |
| danger    | Errors, destructive        |

#### Common Patterns
```tsx
// Card with muted subtitle
<p className="text-foreground">Title</p>
<p className="text-foreground-500">Subtitle</p>

// Input-matching custom element
<div className="bg-default-100 border-default-200 rounded-medium">

// Status indicators
<Chip color="success">Complete</Chip>
<Chip color="danger">Failed</Chip>

// Console/code block
<div className="bg-content2 rounded-medium font-mono text-sm">
```

#### Rules
- Use `foreground` scale for text, `default` scale for UI elements
- Match HeroUI components: `rounded-medium`, `border-medium`, `bg-default-100`
- Don't use arbitrary colors — stick to semantic tokens

## General

- Lint and format after finishing modifying source code.
  - Use the justfile commands.
  - If only typescript has been modified, run only the format and lintingn for typescript
  - If only backend has been modified, run only the format and linting for python
  - If both are modified. Format and lint everything


## justfile commands

- The following recipes from `just` are available.
- Always execute them from the project root folder, where the justfile is located.

```bash
Available recipes:
    build            # Build both apps
    build-api        # Build Python package
    build-web        # Build frontend for production
    check            # Run all checks (lint + format)
    clean            # Clean build artifacts
    default          # List available commands
    dev              # Run API + frontend dev servers
    dev-api          # Run FastAPI backend with reload
    dev-web          # Run Vite frontend
    format           # Format both apps
    format-api       # Format Python with ruff
    format-check     # Check formatting without changes
    format-check-api # Check Python formatting
    format-check-web # Check frontend formatting
    format-web       # Format frontend with prettier
    gen-api          # Generate TypeScript types from OpenAPI
    install          # Install all dependencies
    install-api      # Install Python dependencies
    install-web      # Install frontend dependencies
    lint             # Lint both apps
    lint-api         # Lint Python with ruff
    lint-web         # Lint frontend with eslint
```
