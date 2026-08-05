# PROJECT KNOWLEDGE BASE

**Generated:** 2026-08-05T00:00:00Z
**Commit:** cc3ea88
**Branch:** enhance-stability
**Version:** 0.6.0

## OVERVIEW
Python 3.14.3+ MCP server for GitHub/GitLab PR diff analysis with Clean Architecture (Domain → Application → Infrastructure). FastMCP 3.x, Pydantic v2 (application boundary), anyio async. 249 Python files (133 src + 116 tests), ~50K lines, 44 AGENTS.md files.

## STRUCTURE
```
PRDifferMCP/
├── prdiffer/
│   ├── domain/           # Pure business logic (37 files, 8 packages)
│   ├── infrastructure/   # External integrations (72 files, cache/github/security/utils/vcs)
│   └── application/      # MCP server, components, tool registry (21 files)
├── tests/                # Unit/integration/performance (116 files, ~2300 test defs)
├── scripts/              # Dependency analyzer, benches, git-hooks
├── docs/plans/           # Design plans (e.g. full-diff-correctness-performance)
├── skills/prdiffer/      # Agent skill for MCP tool usage
├── settings.toml         # Dynaconf configuration (236 lines)
└── start-*.sh            # Quality gate scripts (lint, type-check, unittest, server)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add VCS provider** | `prdiffer/domain/vcs_provider_registry.py`, `prdiffer/infrastructure/vcs_providers/` | Implement `VCSDiffRepositoryInterface`, register in registry |
| **Add MCP tool** | `prdiffer/application/tool_registry.py` | Register via `@mcp.tool()` in `ToolRegistry.register_tools()` |
| **Modify DI** | `prdiffer/infrastructure/di_container.py`, `prdiffer/infrastructure/factories/infrastructure_factory.py` | `ServiceContainer` singletons; factory methods for services |
| **Add exception / error code** | `prdiffer/domain/exceptions.py`, `prdiffer/domain/error_codes.py`, `prdiffer/domain/errors.py` | `E{category}{number}_{NAME}` (1xxx–5xxx) |
| **Config changes** | `settings.toml`, `prdiffer/infrastructure/settings.py` | Dynaconf groups: `[default]`, `[performance]`, `[default.auth]` |
| **Retry logic** | `prdiffer/infrastructure/utils/retry/` | `base.py` (339), `handler.py` (135), `models.py` (29), `factories.py` (93) |
| **Caching** | `prdiffer/infrastructure/cache/` | `service.py`, `cache_decorators.py`, `cache_repository.py` (package; shims under subdirs) |
| **Security** | `prdiffer/infrastructure/security/` | `input_validator.py` (326), `injection_detector.py` (216), `sanitizer.py` (140) |
| **Async patterns** | `prdiffer/infrastructure/utils/parallel/executor.py` | 443-line anyio parallel executor |
| **Circuit breaker** | `prdiffer/infrastructure/utils/circuit_breaker_core.py` | Canonical 215-line impl; `utils/circuit_breaker/` is a re-export shim |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| PRDiff | Entity | `prdiffer/domain/entities/pr_diff.py` | Frozen dataclass; `files: tuple[FileDiffResponse, ...]` |
| FilePatchInfo | Entity | `prdiffer/domain/entities/file_patch.py` | Rich domain model (329 lines): priority, smells, validate |
| FileDiffResponse | Entity | `prdiffer/domain/entities/file_diff_response.py` | MCP response DTO (path/status/stats/diff) |
| VCSDiffRepositoryInterface | Interface | `prdiffer/domain/interfaces/vcs_provider.py` | VCS provider contract |
| VCSProviderRegistry | Registry | `prdiffer/domain/vcs_provider_registry.py` | URL-based provider auto-detection |
| ServiceContainer | DI | `prdiffer/infrastructure/di_container.py` | Singleton/transient registration |
| UnifiedRetryHandler | Service | `prdiffer/infrastructure/utils/retry/handler.py` | Context-aware retry + circuit breaker |
| CircuitBreaker | Service | `prdiffer/infrastructure/utils/circuit_breaker_core.py` | CLOSED → OPEN → HALF_OPEN state machine |
| AsyncParallelExecutor | Service | `prdiffer/infrastructure/utils/parallel/executor.py` | anyio task groups + semaphores |
| FastMCPServer | Application | `prdiffer/application/mcp_server.py` | 189-line MCP orchestrator |
| ToolRegistry | Application | `prdiffer/application/tool_registry.py` | 477-line tools: get_pr_diff, approve_pr, describe_pr |
| WebhookHandler | Application | `prdiffer/application/webhook_handler.py` | 171-line webhook cache invalidation |
| HealthEndpoints | Application | `prdiffer/application/health_endpoints.py` | 120-line /health and metrics |
| InputValidator | Security | `prdiffer/infrastructure/security/input_validator.py` | Validation orchestrator + helpers mixin |
| InjectionDetector | Security | `prdiffer/infrastructure/security/injection_detector.py` | Command / path / SQL pattern detection |
| InputSanitizer | Security | `prdiffer/infrastructure/security/sanitizer.py` | String + log sanitization |
| LazyLoggerMixin | Utility | `prdiffer/infrastructure/utils/logger_factory.py` | Lazy logger init (file 123 lines) |
| GitHubPRDiffRepository | Infrastructure | `prdiffer/infrastructure/github_repository.py` | 457-line GitHub PR repository |
| GitLabVCSRepository | Infrastructure | `prdiffer/infrastructure/vcs_providers/gitlab_repository.py` | GitLab VCS provider |

## CONVENTIONS

### Clean Architecture
- **Domain**: Pure Python, no external deps, no I/O. Interfaces + entities + use cases only.
- **Infrastructure**: Implements domain interfaces. Handles network, cache, security, logging.
- **Application**: Orchestrates MCP tools/components. May depend on domain interfaces and factories.
- **Layer direction**: Outer → inner only. Domain must not import application/infrastructure.
- **Analyzer**: `python3 scripts/analyze_dependencies.py --path prdiffer` (AST-based; top-level imports).
- **Current analyzer result**: 1 Application → Infrastructure violation (`application.factory` → `infrastructure.factories.infrastructure_factory`). Additional lazy/in-function infrastructure imports exist for factory fallbacks.

### Dependency Injection
- Constructor injection preferred; optional params with singleton factory fallbacks.
- `ServiceContainer` for singletons; `InfrastructureFactory` / `ApplicationFactory` for creation.
- Many `get_*()` helpers (`get_container`, `get_settings_service`, `get_cache_service`, …).
- Prefer injecting domain Protocols/interfaces over concrete infrastructure types.

### Async
- **anyio** for backend-agnostic async (preferred over raw asyncio).
- `AsyncParallelExecutor` for concurrent file/API work.
- Primitives: `Semaphore`, `Lock`, `Event`, `create_task_group()`.
- Tests largely use `@pytest.mark.asyncio` (pytest-asyncio); production code is anyio-first.

### Configuration
- **Dynaconf** via `settings.toml` + optional `.secrets.toml`.
- Manual caching with `RLock` in `SettingsService` (Dynaconf unhashable → no `@lru_cache`).
- Env overrides: `GITHUB_TOKEN`, `MCP_AUTH_ENABLED`, `MCP_API_KEYS`, `MCP_TRANSPORT`, `MCP_PORT`, `MCP_HOST`.
- `GitHubConfig` frozen dataclass with tuple fields for hashability.
- **Ruff configured** in `pyproject.toml` (E/F/W/Q, line-length 160, double quotes, target py314).

### Error Codes
- Format: `E{category}{number}_{NAME}` (e.g. `E1001_INVALID_URL`).
- Categories: 1xxx validation, 2xxx auth, 3xxx rate limit, 4xxx not found, 5xxx server.
- Constants in `error_codes.py`; helpers/types in `errors.py`; exception hierarchy in `exceptions.py`.

### Testing
- **pytest** markers: `unit`, `integration`, `security` (and asyncio via pytest-asyncio).
- Layout: `tests/unit/{domain,infrastructure,application}`, `tests/integration`, `tests/performance`.
- ~2300 test functions across 100 `test_*.py` files; phase tests at `tests/test_phase{1-4}_improvements.py`.
- Mock external I/O; no live GitHub/GitLab in unit tests.
- Auto-use fixtures: `set_test_environment`, `reset_singletons` in `tests/conftest.py`.

### Build/CI
- **GitHub Actions**: `.github/workflows/pr-quality.yml` runs lint (`ruff check`), type check (`ty check`), and unit tests (`pytest`) on pull requests targeting `main` or `develop` (parallel matrix jobs, `uv sync --frozen --group dev`).
- **Pre-commit** available (`.pre-commit-config.yaml`: ruff, pyright, basic hooks).
- Local quality gates: `start-lint.sh`, `start-type-check.sh` (ty + optional pyright), `start-unittest.sh`.
- Git hooks: `scripts/setup-git-hooks.sh` copies `scripts/git-hooks/pre-push` (type-check + lint).
- Primary type checker in scripts/CI: **ty** (Astral); pyright also configured (`pyrightconfig.json`, pre-commit).

### Python Version
- **requires-python**: `>=3.14.3` (`pyproject.toml`); `.python-version`: `3.14.6`.
- Prefer built-in generics (`list[str]`, `X | None`). ~59 files still use `from typing import …` (documented deviation).

## ANTI-PATTERNS (THIS PROJECT)

### Critical
- **NO imports from outer layers in domain** → Domain stays pure.
- **NO direct PyGithub/python-gitlab in application** → Use infrastructure services/repositories.
- **NO `@lru_cache` on settings** → Manual RLock cache.
- **NO async mixed with blocking I/O** → Offload via AsyncParallelExecutor / anyio.
- **NO `# type: ignore`** → Fix types properly (currently 0 in `prdiffer/`).
- **NO empty catch blocks** → Log or re-raise with context.
- **Never retry 404s for file content** → Added/removed files, not transient errors.
- **NEVER use unverified JWT for auth decisions** → Metadata only; API keys are primary auth.

### Architecture
- **NO business logic in application components** → Domain use cases/entities.
- **NO static plugin registration** → Tools live in `ToolRegistry` (`@mcp.tool()`).
- **NO synchronous blocking on tool path** → Tool handlers are async.
- **NO bypassing circuit breaker** for external APIs when integrated.
- Prefer domain Protocols over reaching into infrastructure from components (lazy factory imports are transitional).

### Security
- **NO command injection** (shell metacharacters, substitution).
- **NO path traversal** (`..`, sensitive absolute paths).
- **NO SQL injection patterns** in free-text inputs.
- **NO hardcoded secrets** → env / `.secrets.toml`.

### Build/Testing
- **NO production logic only in tests**.
- **NO real API calls in unit tests**.
- **NO integration tests under `tests/unit/`**.
- **NO interactive git flags** (`-i`) in scripts/hooks.

### Large Files
- **Prefer modules <500 lines.** Production sources currently stay under 500 lines.
- Large tests remain (e.g. `test_authentication.py` 1145 lines); prefer splitting when editing.

## UNIQUE STYLES

### Entry Point
- `prdiffer/server.py` + console script `prdiffer = "prdiffer.server:main"`.
- Transport-aware diagnostics (stdio must not corrupt JSON-RPC on stdout).
- CLI args override env/settings (`--transport`, `--port`, `--host`, `--path`).
- Dev convenience: `sys.path` injection for direct execution.

### Build Patterns
- Manual quality-gate shell scripts (no Makefile) plus PR CI on `main`/`develop`.
- Pre-push: type-check + lint via version-controlled hooks.
- CI uses frozen lockfile installs (`uv sync --frozen`) — no auto tool upgrades on runners.
- `start-lint.sh --quotes` can rewrite triple-quote style (project-specific).
- Developer wrappers: `start-cc-mmax.sh`, `start-cc-zai.sh`.
- Architecture analyzer exits non-zero on layer violations.

### Organization
- Dual factories: domain interfaces (`domain/factories/`), infrastructure/application implement.
- VCS registry + `supports_repository()` for multi-provider URLs.
- Tools registered in `ToolRegistry` (not a separate plugin package; `application/plugins/` is empty reserved path).
- Cache, circuit breaker, and some utils use **flattened modules + package shims** for backward-compatible imports.

## COMMANDS
```bash
# Environment
uv install              # Install dependencies (see README)
uv install --dev        # Include dev deps when supported by local uv workflow

# Linting
./start-lint.sh --check
./start-lint.sh --fix
./start-lint.sh --format
./start-lint.sh --quotes
./start-lint.sh --all

# Type checking (ty primary in script)
./start-type-check.sh --check
./start-type-check.sh --stats
uv run pyright prdiffer   # Also available via pre-commit

# Tests
./start-unittest.sh --run
./start-unittest.sh --coverage
./start-unittest.sh --parallel
./start-unittest.sh --file <path>
./start-unittest.sh --pattern <pat>

# Server
uv run python prdiffer/server.py
uv run prdiffer --transport http --port 9102
./start-prdiffer-mcp-server.sh

# Architecture
python3 scripts/analyze_dependencies.py --path prdiffer

# Git hooks
./scripts/setup-git-hooks.sh

# CI (PR to main/develop) — same gates as .github/workflows/pr-quality.yml
uv sync --frozen --group dev
uv run ruff check .
uv run ty check
uv run pytest tests -v --tb=short
```

## NOTES

- **CI**: PRs targeting `main` or `develop` must pass Lint, Type check, and Unit tests (GitHub Actions).
- **Auth**: Controlled by `MCP_AUTH_ENABLED` / settings `[default.auth]`; use API keys via `MCP_API_KEYS` when enabled.
- **MCP tools**: `get_pr_diff`, `approve_pr`, `describe_pr`, plus health tool registration.
- **VCS**: GitHub (primary) + GitLab provider implementations; registry auto-detects from URL.
- **Package version**: `pyproject.toml` = `0.6.0`; keep `prdiffer/version.py` in sync when releasing.
- **Python**: 3.14.3+ required; local pin `.python-version` = 3.14.6.
- **AGENTS.md coverage**: 44 files (root + layer/package docs under `prdiffer/`, `tests/`, `scripts/`).
- **Empty reserved dirs**: `application/plugins/`, `application/services/`, `infrastructure/interfaces/` (docs only / placeholders).
