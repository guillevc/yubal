# AGENTS.md

## MCP Tools

### context7

Use context7 MCP to look up documentation for frameworks and libraries before implementing.

**When to use:**

- Unfamiliar with a framework's API
- Need to check current best practices
- Unsure about configuration options
- Implementing features with libraries not frequently used

**Examples:**

- Before creating WXT extension: look up WXT docs
- Before using a new HeroUI component: look up component props and variants
- Before configuring beets plugins: look up beets documentation

**Don't use when:**

- Already confident about the API
- Simple/common patterns (basic React, standard Python)
- Information is already in this file or project docs

## Decision Making

- Be specific about the solution you are proposing. Show code examples and internal behavior.
- Prompt before making importatn decisions. Provide as much information as possible. Give advice but lay out all possibilities.
- Pragmatic over clever
- Minimal dependencies
- Modern Python (3.12+, Pydantic v2, etc.)
- Question assumptions before implementing
- When suggesting libraries, tools, or patterns:
  - Compare 2-3 options with trade-offs before choosing
  - Check maintenance status (last commit, open issues)
  - Prefer modern, actively maintained solutions
  - Consider what's already in the stack
  - Don't just grab the first library that solves the problem.
- Lint and format after finishing modifying source code.
  - Use the justfile commands.
  - If only typescript has been modified, run only the format and lintingn for typescript
  - If only backend has been modified, run only the format and linting for python
  - If both are modified. Format and lint everything

## API guidelines

- Run `just gen-api` (from project root) if there have been API changes.
- Use `__init__.py` empty files for packages.
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
| --------- | -------------------------- |
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

## justfile commands

- The following recipes from `just` are available.
- Always execute them from the project root folder, where the justfile is located.

```bash
Available recipes:
    build            # Build [alias: b]
    build-api
    build-web
    check            # [alias: c]
    clean
    default
    dev              # Dev [alias: d]
    dev-api
    dev-web
    format           # Format [alias: f]
    format-api
    format-check
    format-check-api
    format-check-web
    format-web
    gen-api          # Utils
    install          # [alias: i]
    install-api
    install-web
    lint             # Lint [alias: l]
    lint-api
    lint-web
    typecheck        # Typecheck [alias: t]
    typecheck-api
    typecheck-web
```
