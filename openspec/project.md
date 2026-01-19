# Project Context

## Purpose

PRDiffer is an MCP (Model Context Protocol) server that provides GitHub PR diff analysis capabilities with full file context. The server enables AI assistants and code review tools to retrieve comprehensive PR diff information including:

- Complete file content before and after changes (not just minimal hunks)
- Commit messages and PR metadata
- File change statistics and edit type classification
- Pattern-based file filtering for relevant code files

**Primary Use Cases:**
- AI-powered code review assistants
- Automated PR analysis tools
- Code change summarization systems
- Integration with Claude Code and other MCP-compatible clients

## Tech Stack

### Core Technologies

- **Python 3.14+** - Primary language (requires Python 3.14.1 or higher)
- **FastMCP** - MCP server framework for tool exposure
- **PyGithub** - GitHub API integration
- **Pydantic** - Data validation and serialization
- **anyio** - Async compatibility layer (backend-agnostic)

### Infrastructure
- **Dynaconf** - TOML-based configuration management
- **uvicorn** - ASGI server for HTTP transport
- **uvloop** - High-performance event loop
- **httpx** - Async HTTP client

### Development Tools
- **uv** - Python package manager and runner
- **Ruff** - Linting and formatting
- **ty** - Static type checking (Astral)
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting

## Project Conventions

### Code Style

**Linting & Formatting:**
- Use Ruff for all linting and formatting (`./start-lint.sh --all`)
- Run type checking with ty (`./start-type-check.sh --check`)
- All code must pass linting and type checking before push (enforced by pre-push hook)

**Type Annotations:**
- All functions must have complete type annotations
- Use `Optional[T]` for nullable types
- Use `Protocol` classes for structural typing
- Avoid `Any` type where possible

**Naming Conventions:**
- Classes: `PascalCase` (e.g., `PRDiffRepository`, `CacheService`)
- Functions/methods: `snake_case` (e.g., `get_pr_diff`, `validate_url`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- Private methods: `_leading_underscore` (e.g., `_build_patch`, `_filter_files`)
- Interfaces: Suffix with `Interface` (e.g., `CacheServiceInterface`)
- Protocols: Suffix with `Protocol` (e.g., `URLValidatorProtocol`)

**Imports:**
- Group imports: stdlib, third-party, local
- Use absolute imports within package
- Avoid circular imports through interface-based design

### Architecture Patterns

**Clean Architecture:**
The codebase follows Clean Architecture with strict layer separation:

```
Application Layer (MCP Server, Components)
         ↓ (depends on)
Domain Layer (Entities, Use Cases, Interfaces)
         ↑ (implemented by)
Infrastructure Layer (GitHub, Caching, Logging)
```

**Key Principles:**
- **Dependency Inversion**: Domain defines interfaces, infrastructure implements
- **Single Responsibility**: Each class has one clear purpose
- **Interface Segregation**: Small, focused interfaces
- **Factory Pattern**: Use `InfrastructureFactory` for service creation
- **Singleton Pattern**: Shared services (cache, logger, settings) use singletons

**Layer Guidelines:**

| Layer | Purpose | Dependencies Allowed |
|-------|---------|---------------------|
| Domain | Business logic, entities, interfaces | None (pure Python) |
| Application | Orchestration, MCP protocol | Domain layer only |
| Infrastructure | External integrations | Domain + external libraries |

**File Organization:**
```
prdiffer/
├── domain/           # No external dependencies
│   ├── entities/     # Core business objects (dataclasses, Pydantic models)
│   ├── repositories/ # Repository interfaces
│   ├── services/     # Service interfaces
│   ├── usecases/     # Business logic orchestration
│   └── factories/    # Factory interfaces
├── application/      # MCP server and components
│   ├── components/   # URL validator, rate limiter, etc.
│   └── interfaces/   # Protocol definitions
└── infrastructure/   # External integrations
    ├── github/       # GitHub API components
    ├── security/     # Input validation
    ├── utils/        # Utilities (retry, patterns, diff)
    ├── logging/      # Console logger
    ├── factories/    # Factory implementations
    └── services/     # Service implementations
```

### Testing Strategy

**Test Organization:**
- `tests/unit/` - Isolated unit tests
- `tests/integration/` - Integration tests with external services
- Test files match source: `test_<module>.py`

**Test Markers:**
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Tests with external dependencies
- `@pytest.mark.slow` - Long-running tests

**Running Tests:**
```bash
./start-unittest.sh --run           # Run all tests
./start-unittest.sh --coverage      # With coverage
./start-unittest.sh --parallel      # Parallel execution
```

**Testing Guidelines:**
- Use `pytest.fixture` for test setup
- Mock external services in unit tests
- Use `pytest.mark.asyncio` for async tests
- Aim for high coverage on domain and application layers
- Test security validation thoroughly

### Git Workflow

**Branch Strategy:**
- `main` - Production-ready code
- Feature branches for development

**Pre-Push Validation:**
Git hooks enforce quality checks before push:
1. Type checking (`./start-type-check.sh`)
2. Linting (`./start-lint.sh --all`)

**Setup hooks:**
```bash
./scripts/setup-git-hooks.sh
```

**Commit Message Format:**
- Use imperative mood: "Add feature" not "Added feature"
- Keep subject line under 72 characters
- Reference issues when applicable

## Domain Context

**GitHub PR Processing:**
- PRs are identified by owner/repo/number tuple
- Full file content is fetched for base and head commits
- Merge base commits used for accurate diff comparison (handles parallel merges)
- Files filtered by configurable patterns (ignore_patterns, valid_extensions)

**Diff Generation:**
- Uses `difflib.SequenceMatcher` for line-by-line comparison
- Generates full-file unified diffs (complete context, not minimal hunks)
- Supports multiple file encodings (UTF-8, iso-8859-1, latin-1, ascii, utf-16)

**Caching Strategy:**
- Commit-based cache invalidation (SHA as part of cache key)
- MD5-hashed cache keys for memory efficiency
- Automatic refresh when new commits pushed to PR

**Edit Types:**
- `ADDED` - New file
- `DELETED` - Removed file
- `MODIFIED` - Changed file
- `RENAMED` - Renamed file
- `UNKNOWN` - Unrecognized status

## Important Constraints

**Technical Constraints:**
- Requires Python 3.14+ (bleeding edge requirement)
- In-memory caching only (no external cache stores)
- Single-process design (no distributed caching)
- GitHub API rate limits apply (5000 requests/hour for authenticated)

**Security Constraints:**
- All user inputs must pass `InputValidator` validation
- No shell command execution with user input
- No path traversal in file operations
- Safe logging (sanitized values to prevent log injection)
- OWASP Top 10 prevention for injection attacks

**Performance Constraints:**
- Max 50 files per PR by default (`max_files_allowed`)
- 30-second timeout per file operation
- Circuit breaker prevents cascading failures (5 failures threshold)
- Parallel processing only when files > threshold (default: 3)

## External Dependencies

**GitHub API:**
- Uses PyGithub library for REST API access
- Authentication via `GITHUB_TOKEN` environment variable
- Supports anonymous access (lower rate limits)
- Rate limiting and retry logic built-in

**MCP Protocol:**
- Implements Model Context Protocol for AI assistant integration
- Supports multiple transports: stdio, http, sse, streamable-http
- Default HTTP server on port 9102

**Configuration:**
- `settings.toml` - Primary configuration file
- Environment variables for secrets
- Dynaconf for TOML parsing with environment overrides

**Key Environment Variables:**
| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | GitHub API authentication |
| `TRANSPORT` | MCP transport mode override |
| `PORT` | Server port override |
