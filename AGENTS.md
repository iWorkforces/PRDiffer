# PROJECT KNOWLEDGE BASE

**Generated:** 2026-08-05T04:00:00Z
**Commit:** 915d947
**Branch:** enhance-stability
**Version:** 0.6.0

## OVERVIEW
Python 3.14.3+ MCP server for GitHub/GitLab PR diff analysis with Clean Architecture (Domain → Application → Infrastructure). FastMCP 3.x, Pydantic v2 (application boundary), anyio async. **268** Python files (**139** src + **129** tests), ~53K lines, **44** AGENTS.md files.

Strict full-context diffs are **all-or-nothing**: complete ordered multi-file context or structured `E5020_FULL_DIFF_INCOMPLETE` (no partial files, no truncation notices).

## STRUCTURE
```
PRDifferMCP/
├── prdiffer/
│   ├── domain/           # Pure business logic (41 modules, 7 packages)
│   ├── infrastructure/   # External integrations (74 modules: cache/github/security/utils/vcs)
│   └── application/      # MCP server, components, tool registry (21 modules)
├── tests/                # Unit/integration/performance (~2390 test defs, 113 test_*.py)
├── scripts/              # Dependency analyzer, benches, git-hooks
├── docs/plans/           # Design plans (full-diff-correctness-performance)
├── skills/prdiffer/      # Agent skill for MCP tool usage
├── .github/workflows/    # pr-quality.yml (lint / ty / pytest on PR → main|develop)
├── settings.toml         # Dynaconf configuration (240 lines)
└── start-*.sh            # Quality gate scripts (lint, type-check, unittest, server)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add VCS provider** | `domain/vcs_provider_registry.py`, `infrastructure/vcs_providers/` | Implement `VCSDiffRepositoryInterface`, register in registry |
| **Add MCP tool** | `application/tool_registry.py` | Register via `@mcp.tool()` in `ToolRegistry.register_tools()` |
| **Modify DI** | `infrastructure/di_container.py`, `infrastructure/factories/` | `ServiceContainer` singletons; `InfrastructureFactory` creation |
| **Add exception / error code** | `domain/exceptions.py`, `error_codes.py`, `errors.py` | `E{category}{number}_{NAME}` (1xxx–5xxx); E5020 full-diff |
| **Config changes** | `settings.toml`, `infrastructure/settings.py`, `domain/config/github_config.py` | Dynaconf + frozen `GitHubConfig` (timeouts, size limits, parallel flags) |
| **Strict full-diff path** | `infrastructure/github/` + `services/pr_diff_service.py` + `domain/usecases/pr_diff_usecases.py` | Inventory → content → ordered generate → session reader → MCP |
| **Retry logic** | `infrastructure/utils/retry/` | `base.py` (339), `handler.py` (135), `models.py` (29), `factories.py` (93) |
| **Caching** | `infrastructure/cache/` | `service.py` (340), `cache_decorators.py` (248), v2 PR-diff keys |
| **Security** | `infrastructure/security/` | `input_validator.py` (326), `injection_detector.py` (216), `sanitizer.py` (140) |
| **Async / indexed batch** | `infrastructure/utils/parallel/executor.py` | 608-line anyio executor + `execute_indexed_batch` |
| **Circuit breaker** | `infrastructure/utils/circuit_breaker_core.py` | Canonical 215-line impl; package dir is re-export shim |
| **Benchmarks** | `scripts/bench_diff_generation.py` | Deterministic strict-v1 matrix; evidence under `.omo/` (gitignored) |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| PRDiff | Entity | `domain/entities/pr_diff.py` | Frozen dataclass; `files: tuple[FileDiffResponse, ...]` |
| FilePatchInfo | Entity | `domain/entities/file_patch.py` | Rich domain model (329): priority, smells, validate |
| FileDiffResponse | Entity | `domain/entities/file_diff_response.py` | MCP DTO; optional `previous_path` for renames |
| FileContentAvailable / Unavailable | Entity | `domain/entities/file_content.py` | Typed content acquisition results |
| GeneratedFileDiff | Entity | `domain/entities/generated_file_diff.py` | Ordered full-context generation result |
| PRDiffCacheEntryV2 | Entity | `domain/entities/pr_diff_cache.py` | Versioned cache payload (`github-full-diff-v2`) |
| FullDiffIncompleteError | Exception | `domain/exceptions.py` | E5020 fail-closed completeness (562-line module) |
| GitHubConfig | Config | `domain/config/github_config.py` | Authoritative timeouts, size limits, parallel flags (266) |
| PRDiffReader / session | Interface | `domain/interfaces/pr_diff_reader.py` | Session-capable reader contract |
| VCSDiffRepositoryInterface | Interface | `domain/interfaces/vcs_provider.py` | VCS provider contract |
| VCSProviderRegistry | Registry | `domain/vcs_provider_registry.py` | URL-based provider auto-detection |
| GetPRDiffUseCase | Use case | `domain/usecases/pr_diff_usecases.py` | Session path vs legacy; v2 cache unwrap (134) |
| ServiceContainer | DI | `infrastructure/di_container.py` | Singleton/transient registration (203) |
| UnifiedRetryHandler | Service | `infrastructure/utils/retry/handler.py` | Context-aware retry + circuit breaker |
| CircuitBreaker | Service | `infrastructure/utils/circuit_breaker_core.py` | CLOSED → OPEN → HALF_OPEN |
| AsyncParallelExecutor | Service | `infrastructure/utils/parallel/executor.py` | anyio task groups; indexed all-or-error batch (608) |
| GitHubPRDiffSession | Infra | `infrastructure/github/pr_diff_session.py` | anyio thread isolation + capacity limiter (213) |
| FileProcessor | Infra | `infrastructure/github/file_processor.py` | Ordered selected-file assembly (544) |
| DiffGenerator | Infra | `infrastructure/github/diff_generator.py` | Full-context ordered generation (468) |
| Inventory admission | Infra | `infrastructure/github/inventory.py` | changed_files vs enumeration hard-fail (126) |
| GitHubPRDiffService | Infra | `infrastructure/services/pr_diff_service.py` | Maps GeneratedFileDiff → public responses (527) |
| FastMCPServer | Application | `application/mcp_server.py` | MCP orchestrator (191) |
| ToolRegistry | Application | `application/tool_registry.py` | Tools: get_pr_diff, approve_pr, describe_pr (481) |
| WebhookHandler | Application | `application/webhook_handler.py` | Webhook cache invalidation (171) |
| HealthEndpoints | Application | `application/health_endpoints.py` | /health and metrics (120) |
| InputValidator | Security | `infrastructure/security/input_validator.py` | Validation orchestrator |
| GitHubPRDiffRepository | Infra | `infrastructure/github_repository.py` | GitHub PR repository (461) |
| GitLabVCSRepository | Infra | `infrastructure/vcs_providers/gitlab_repository.py` | GitLab VCS provider |

## CONVENTIONS

### Clean Architecture
- **Domain**: Pure Python, no external deps, no I/O. Interfaces + entities + use cases only.
- **Infrastructure**: Implements domain interfaces. Handles network, cache, security, logging.
- **Application**: Orchestrates MCP tools/components. May depend on domain interfaces and factories.
- **Layer direction**: Outer → inner only. Domain must not import application/infrastructure.
- **Analyzer**: `python3 scripts/analyze_dependencies.py --path prdiffer` (AST; top-level imports).
- **Current analyzer result**: 1 Application → Infrastructure violation (`application.factory` → `infrastructure.factories.infrastructure_factory`). Lazy/in-function infrastructure imports exist for factory fallbacks.

### Full-diff completeness (strict)
- Selected files must all succeed or raise **E5020** with `FullDiffIncompleteReason`.
- No truncation notices / partial payloads on size limit (`RESPONSE_SIZE_LIMIT`).
- Content cache keys: `(repo_full_name, path, ref)`; unavailable results are not cached as success.
- PR-diff response cache: **v2 only** (`github-full-diff-v2`); legacy entries ignored.
- Parallel fetch/generation is **opt-in** (default serialized, capacity 1).
- PyGithub blocking calls stay off the event loop via session + `anyio.to_thread` + limiter.

### Dependency Injection
- Constructor injection preferred; optional params with singleton factory fallbacks.
- `ServiceContainer` for singletons; `InfrastructureFactory` / `ApplicationFactory` for creation.
- Prefer injecting domain Protocols/interfaces over concrete infrastructure types.

### Async
- **anyio** for backend-agnostic async (preferred over raw asyncio).
- `AsyncParallelExecutor` + `execute_indexed_batch` for concurrent work with identity preservation.
- Tests largely use `@pytest.mark.asyncio` (pytest-asyncio); production code is anyio-first.

### Configuration
- **Dynaconf** via `settings.toml` + optional `.secrets.toml`.
- Manual caching with `RLock` in `SettingsService` (Dynaconf unhashable → no `@lru_cache`).
- Env overrides: `GITHUB_TOKEN`, `MCP_AUTH_ENABLED`, `MCP_API_KEYS`, `MCP_TRANSPORT`, `MCP_PORT`, `MCP_HOST`.
- `GitHubConfig` frozen dataclass: `timeout` (30), `pr_diff_request_timeout_seconds` (180), size limits, `parallel_*` default false.
- **Ruff** configured in `pyproject.toml` (E/F/W/Q, line-length 160, double quotes, target py314).

### Error Codes
- Format: `E{category}{number}_{NAME}` (e.g. `E1001_INVALID_URL`, `E5020_FULL_DIFF_INCOMPLETE`).
- Categories: 1xxx validation, 2xxx auth, 3xxx rate limit, 4xxx not found, 5xxx server.
- Constants in `error_codes.py`; helpers/types in `errors.py`; exception hierarchy in `exceptions.py`.

### Testing
- **pytest** markers: `unit`, `integration`, `security`, `slow`, `thread_safety` (and asyncio via pytest-asyncio).
- Layout: `tests/unit/{domain,infrastructure,application}`, `tests/integration`, `tests/performance`.
- ~2390 test functions across 113 `test_*.py` files; phase tests at `tests/test_phase{1-4}_improvements.py`.
- Mock external I/O; no live GitHub/GitLab in unit tests (real API suite always-skipped).
- Auto-use fixtures: `set_test_environment`, `reset_singletons` in `tests/conftest.py`.

### Build/CI
- **GitHub Actions**: `.github/workflows/pr-quality.yml` — Lint (`ruff check`), Type check (`ty check`), Unit tests (`pytest`) on PRs to `main` or `develop` (parallel matrix, `uv sync --frozen --group dev`).
- **Pre-commit** available (`.pre-commit-config.yaml`: ruff, pyright, basic hooks).
- Local quality gates: `start-lint.sh` (prefers `uv run ruff`), `start-type-check.sh` (ty), `start-unittest.sh`.
- Git hooks: `scripts/setup-git-hooks.sh` copies `scripts/git-hooks/pre-push` (type-check + lint).
- Primary type checker in scripts/CI: **ty** (Astral); pyright also configured.

### Python Version
- **requires-python**: `>=3.14.3` (`pyproject.toml`); `.python-version`: `3.14.6`.
- Prefer built-in generics (`list[str]`, `X | None`). ~64 files still use `from typing import …` (documented deviation).
- **0** `# type: ignore` in `prdiffer/`.

## ANTI-PATTERNS (THIS PROJECT)

### Critical
- **NO imports from outer layers in domain** → Domain stays pure.
- **NO direct PyGithub/python-gitlab in application** → Use infrastructure services/repositories.
- **NO `@lru_cache` on settings** → Manual RLock cache.
- **NO async mixed with blocking I/O** → Offload via session / AsyncParallelExecutor / anyio.
- **NO `# type: ignore`** → Fix types properly.
- **NO empty catch blocks** → Log or re-raise with context.
- **Never retry 404s for file content** → Added/removed files, not transient errors.
- **NEVER use unverified JWT for auth decisions** → Metadata only; API keys are primary auth.
- **NO partial full-diff success** → E5020 fail-closed for incomplete/oversized/unavailable selected files.

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
- Prefer modules **&lt;500 lines** when adding features; extract packages if growing.
- Current production hotspots &gt;500: `domain/exceptions.py` (562), `github/file_processor.py` (544), `services/pr_diff_service.py` (527), `parallel/executor.py` (608).
- Large tests remain (e.g. `test_authentication.py` 1145); prefer splitting when editing.

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
- `start-lint.sh` detects project-local ruff via `uv run ruff` (not bare PATH).
- `start-lint.sh --quotes` can rewrite triple-quote style (project-specific).
- Developer wrappers: `start-cc-mmax.sh`, `start-cc-zai.sh`.
- Architecture analyzer exits non-zero on layer violations.

### Organization
- Dual factories: domain interfaces (`domain/factories/`), infrastructure/application implement.
- VCS registry + `supports_repository()` for multi-provider URLs.
- Tools registered in `ToolRegistry` (not a separate plugin package; `application/plugins/` is empty reserved path).
- Cache, circuit breaker, and some utils use **flattened modules + package shims** for backward-compatible imports.
- GitHub full-diff pipeline is package-local under `infrastructure/github/` with service orchestration in `services/pr_diff_service.py`.

## COMMANDS
```bash
# Environment
uv sync --group dev     # Install project + dev deps from lockfile
uv run <cmd>            # Run tools in project env

# Linting
./start-lint.sh --check
./start-lint.sh --fix
./start-lint.sh --format
./start-lint.sh --quotes
./start-lint.sh --all
# or: uv run ruff check . && uv run ruff format --check .

# Type checking (ty primary in script/CI)
./start-type-check.sh --check
./start-type-check.sh --stats
uv run ty check
uv run pyright prdiffer   # Also available via pre-commit

# Tests
./start-unittest.sh --run
./start-unittest.sh --coverage
./start-unittest.sh --parallel
./start-unittest.sh --file <path>
./start-unittest.sh --pattern <pat>
# or: uv run pytest tests -v --tb=short

# Server
uv run python prdiffer/server.py
uv run prdiffer --transport http --port 9102
./start-prdiffer-mcp-server.sh

# Architecture
python3 scripts/analyze_dependencies.py --path prdiffer

# Full-diff benchmark (deterministic; no network)
uv run python scripts/bench_diff_generation.py --matrix strict-v1 --phase baseline --modes sync-current

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
- **MCP tools**: `get_pr_diff`, `approve_pr`, `describe_pr`, plus health tool registration. Diff responses are full-context all-or-nothing.
- **VCS**: GitHub (primary, session-isolated full-diff) + GitLab provider; registry auto-detects from URL.
- **Package version**: `pyproject.toml` = `0.6.0`; keep `prdiffer/version.py` in sync when releasing.
- **Python**: 3.14.3+ required; local pin `.python-version` = 3.14.6.
- **AGENTS.md coverage**: 44 files (root + layer/package docs under `prdiffer/`, `tests/`, `scripts/`).
- **Empty reserved dirs**: `application/plugins/`, `application/services/`, `application/interfaces/`, `infrastructure/interfaces/` (docs only / placeholders).
- **Analyzer layers**: Application 21, Domain 41, Infrastructure 74 modules (139 total).
