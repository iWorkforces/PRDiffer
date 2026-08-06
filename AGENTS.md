# PROJECT KNOWLEDGE BASE

**Generated:** 2026-08-05T12:50:34Z
**Commit:** f915e6b
**Branch:** develop
**Version:** 0.6.1

## OVERVIEW
Python 3.14.3+ MCP server for GitHub/GitLab PR (merge request) diff analysis with Clean Architecture (Domain → Application → Infrastructure). FastMCP 3.x, Pydantic v2 (application boundary), anyio async. **292** Python files (**146** src + **146** tests), ~20K src / ~38K test lines, **44** AGENTS.md files. **~2515** test defs across **130** `test_*.py` files.

Strict full-context diffs are **all-or-nothing**: complete ordered multi-file context or structured `E5020_FULL_DIFF_INCOMPLETE` (no partial files, no truncation notices). Both GitHub and GitLab use session-scoped open/build/close paths. GitHub head/base content can load in one interleaved multi-ref batch (`FileContentRequest` / `get_files_content_multi_ref_batch`).

## STRUCTURE
```
PRDifferMCP/
├── prdiffer/
│   ├── domain/           # Pure business logic (42 modules, 7 packages)
│   ├── infrastructure/   # External integrations (80 modules: cache/github/security/utils/vcs)
│   └── application/      # MCP server, components, tool registry (21 modules)
├── tests/                # Unit/integration/performance (~2515 test defs, 130 test_*.py)
├── scripts/              # Dependency analyzer, benches, git-hooks
├── docs/plans/           # Design plans (full-diff + gitlab-strict-full-diff)
├── skills/prdiffer/      # Agent skill for MCP tool usage
├── .github/workflows/    # pr-quality.yml (lint / ty / pytest on PR → main|develop)
├── settings.toml         # Dynaconf configuration (~257 lines)
├── .env.example          # Tokens + GITLAB_ALLOWED_HOSTS template
└── start-*.sh            # Quality gates + start-prdiffer-mcp-server.sh
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add VCS provider** | `domain/vcs_provider_registry.py`, `infrastructure/vcs_providers/` | Implement `VCSDiffRepositoryInterface`, register in registry |
| **Add MCP tool** | `application/tool_registry.py` | Register via `@mcp.tool()` in `ToolRegistry.register_tools()` |
| **Modify DI** | `infrastructure/di_container.py`, `infrastructure/factories/` | `ServiceContainer` singletons; `InfrastructureFactory` creation |
| **Add exception / error code** | `domain/exceptions.py`, `error_codes.py`, `errors.py` | `E{category}{number}_{NAME}` (1xxx–5xxx); E5020 full-diff |
| **Config changes** | `settings.toml`, `.env` / `.env.example`, `infrastructure/settings.py`, `domain/config/` | Dynaconf + frozen `GitHubConfig` / `GitLabConfig` |
| **GitHub strict full-diff** | `infrastructure/github/` + `services/pr_diff_service.py` + `domain/usecases/pr_diff_usecases.py` | Inventory → multi-ref content → ordered generate → session → MCP |
| **GitLab strict full-diff** | `infrastructure/vcs_providers/gitlab_*.py` | Version pin → inventory → content → assembler → session reader |
| **GitLab host policy** | `domain/config/gitlab_config.py`, `settings.toml`, env `GITLAB_ALLOWED_HOSTS` | Default `gitlab.com`; opt-in custom hosts |
| **URL parse (MCP)** | `application/utils/pr_url_parser.py` | `parse_pr_target` → GitHub/GitLab + `base_url` |
| **URL parse (infra)** | `infrastructure/utils/url_parser.py` | Nested namespaces; custom GitLab hosts |
| **Multi-ref content batch** | `domain/entities/file_content.py`, `domain/services/github_api.py`, `infrastructure/github/client_operations.py` | `FileContentRequest`/`Response` + `get_files_content_multi_ref_batch` |
| **Retry logic** | `infrastructure/utils/retry/` | `base.py`, `handler.py`, `models.py`, `factories.py` |
| **Caching** | `infrastructure/cache/` | GitHub v2 + GitLab v1 strict keys; unwrap rejects legacy |
| **Security** | `infrastructure/security/` | `input_validator.py`, `injection_detector.py`, `sanitizer.py` |
| **Async / indexed batch** | `infrastructure/utils/parallel/executor.py` | anyio executor (~601) + `execute_indexed_batch`; per-batch semaphore |
| **Circuit breaker** | `infrastructure/utils/circuit_breaker_core.py` | Canonical 215-line impl; package dir is re-export shim |
| **Benchmarks** | `scripts/bench_diff_generation.py` | Deterministic strict-v1 matrix; evidence under `.omo/` (gitignored) |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| PRDiff | Entity | `domain/entities/pr_diff.py` | Frozen dataclass; `files: tuple[FileDiffResponse, ...]` |
| FilePatchInfo | Entity | `domain/entities/file_patch.py` | Rich domain model (~347): priority, smells, modes, validate |
| FileDiffResponse | Entity | `domain/entities/file_diff_response.py` | MCP DTO; optional `previous_path` for renames |
| FileContentAvailable / Unavailable | Entity | `domain/entities/file_content.py` | Typed content acquisition results |
| FileContentRequest / Response | Entity | `domain/entities/file_content.py` | Ref-qualified multi-ref content lookup identity |
| GeneratedFileDiff | Entity | `domain/entities/generated_file_diff.py` | Ordered full-context generation result |
| StrictPRDiffCacheIdentity | Entity | `domain/entities/pr_diff_cache.py` | Provider-neutral key + validation token |
| FullDiffIncompleteError | Exception | `domain/exceptions.py` | E5020 fail-closed completeness (~580-line module) |
| GitHubConfig | Config | `domain/config/github_config.py` | Timeouts, size limits (`max_total_chars` 600k), parallel flags (~266) |
| GitLabConfig | Config | `domain/config/gitlab_config.py` | Limits + `allowed_hosts` (~121) |
| PRDiffReader / session | Interface | `domain/interfaces/pr_diff_reader.py` | Session-capable reader contract |
| VCSDiffRepositoryInterface | Interface | `domain/interfaces/vcs_provider.py` | VCS provider contract |
| VCSProviderRegistry | Registry | `domain/vcs_provider_registry.py` | URL-based provider auto-detection |
| GetPRDiffUseCase | Use case | `domain/usecases/pr_diff_usecases.py` | Session path (+ optional `base_url`); legacy fallback (~148) |
| ServiceContainer | DI | `infrastructure/di_container.py` | Singleton/transient registration (~203) |
| UnifiedRetryHandler | Service | `infrastructure/utils/retry/handler.py` | Context-aware retry + circuit breaker |
| CircuitBreaker | Service | `infrastructure/utils/circuit_breaker_core.py` | CLOSED → OPEN → HALF_OPEN |
| AsyncParallelExecutor | Service | `infrastructure/utils/parallel/executor.py` | anyio task groups; per-batch semaphore; indexed all-or-error (~601) |
| GitHubPRDiffSession | Infra | `infrastructure/github/pr_diff_session.py` | anyio thread isolation + capacity limiter (~223) |
| FileProcessor | Infra | `infrastructure/github/file_processor.py` | Ordered selected-file assembly; multi-ref head/base (~595) |
| DiffGenerator | Infra | `infrastructure/github/diff_generator.py` | Full-context ordered generation (~517) |
| Inventory admission | Infra | `infrastructure/github/inventory.py` | changed_files vs enumeration hard-fail (~126) |
| GitHubPRDiffService | Infra | `infrastructure/services/pr_diff_service.py` | Maps GeneratedFileDiff → public responses (~527) |
| GitLabRuntime | Infra | `infrastructure/vcs_providers/gitlab_runtime.py` | Shared limiter; per-call base_url/deadline (~367) |
| GitLabOperations | Infra | `infrastructure/vcs_providers/gitlab_operations.py` | Immutable MR version pin (`select_with_client`) (~264) |
| GitLabSessionPRDiffReader | Infra | `infrastructure/vcs_providers/gitlab_diff_session.py` | Open/build/close strict MR session (~224) |
| FastMCPServer | Application | `application/mcp_server.py` | MCP orchestrator (~191) |
| ToolRegistry | Application | `application/tool_registry.py` | Tools: get_pr_diff, approve_pr, describe_pr (~496) |
| WebhookHandler | Application | `application/webhook_handler.py` | Webhook cache invalidation (~171) |
| HealthEndpoints | Application | `application/health_endpoints.py` | /health and metrics (~120) |
| InputValidator | Security | `infrastructure/security/input_validator.py` | Validation orchestrator (~326) |
| GitHubPRDiffRepository | Infra | `infrastructure/github_repository.py` | GitHub PR repository (~462) |
| GitLabVCSRepository | Infra | `infrastructure/vcs_providers/gitlab_repository.py` | GitLab VCS adapter (~149) |

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
- Aggregate public budget: `diff.max_total_chars` default **600_000** (`DEFAULT_MAX_TOTAL_CHARS`).
- Content cache keys: `(repo_full_name, path, ref)`; unavailable results are not cached as success.
- PR-diff response cache: **GitHub** `github-full-diff-v2`; **GitLab** `gitlab-full-diff-v1:{host}:…` (host/port-aware); legacy entries ignored.
- Parallel fetch/generation defaults **on** (`performance.parallel_* = true`); capacity uses `github.max_concurrent` / `gitlab.max_concurrent` (disable flags for serialized capacity 1).
- GitHub multi-ref head/base: when `parallel_head_base_fetch_enabled`, one interleaved `get_files_content_multi_ref_batch` (provider order; one capacity bound for all refs).
- Blocking SDK calls stay off the event loop via session + `anyio.to_thread` / `GitLabRuntime.run_blocking` + limiter.
- GitLab equal-content equal-mode modified → hard E5020 (no silent no-op).

### Dependency Injection
- Constructor injection preferred; optional params with singleton factory fallbacks.
- `ServiceContainer` for singletons; `InfrastructureFactory` / `ApplicationFactory` for creation.
- Prefer injecting domain Protocols/interfaces over concrete infrastructure types.

### Async
- **anyio** for backend-agnostic async (preferred over raw asyncio).
- `AsyncParallelExecutor` + `execute_indexed_batch` for concurrent work with identity preservation.
- Executor creates a **fresh semaphore per batch** (safe across independent anyio event loops / threads).
- Tests largely use `@pytest.mark.asyncio` (pytest-asyncio); production code is anyio-first. Some modules use `@pytest.mark.anyio`.

### Configuration
- **Dynaconf** via `settings.toml` + optional `.secrets.toml`.
- Manual caching with `RLock` in `SettingsService` (Dynaconf unhashable → no `@lru_cache`).
- Env overrides: `GITHUB_TOKEN`, `GITLAB_TOKEN`, `GITLAB_ALLOWED_HOSTS` (CSV), `MCP_AUTH_ENABLED`, `MCP_API_KEYS`, `MCP_TRANSPORT`, `MCP_PORT`, `MCP_HOST`, `MAX_FILES_ALLOWED`, `GITHUB_IGNORE_PATTERNS`.
- Copy `.env.example` → `.env`; `start-prdiffer-mcp-server.sh` sources `.env`.
- `GitHubConfig` frozen dataclass: `timeout` (30), `pr_diff_request_timeout_seconds` (180), `max_total_chars` (600_000), size limits, `parallel_*` default true.
- `GitLabConfig` frozen slotted: same timeout shape + `allowed_hosts` default `("gitlab.com",)`.
- **Ruff** configured in `pyproject.toml` (E/F/W/Q, line-length 160, double quotes, target py314).

### Error Codes
- Format: `E{category}{number}_{NAME}` (e.g. `E1001_INVALID_URL`, `E5020_FULL_DIFF_INCOMPLETE`).
- Categories: 1xxx validation, 2xxx auth, 3xxx rate limit, 4xxx not found, 5xxx server.
- GitLab ops: E2006 (401), E2007 (403), E3006 (429), E5021 (5xx), E4001/E4002/E4003 (not found), E5004 timeout, E5019 connection.
- Constants in `error_codes.py`; helpers/types in `errors.py`; exception hierarchy in `exceptions.py`.

### Testing
- **pytest** markers: `unit`, `integration`, `security`, `slow`, `thread_safety` (and asyncio via pytest-asyncio).
- Layout: `tests/unit/{domain,infrastructure,application}`, `tests/integration`, `tests/performance`.
- ~2515 test functions across 130 `test_*.py` files; phase tests at `tests/test_phase{1-4}_improvements.py`.
- Multi-ref suite: `test_file_content_multi_ref*`, `test_file_processor_multi_ref.py`, `test_async_parallel_executor_cross_loop.py`.
- GitLab strict suite: unit (`vcs_providers/`, `test_gitlab_*`), integration `test_gitlab_strict_full_diff.py`, performance capacity/deadline.
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
- Prefer built-in generics (`list[str]`, `X | None`). ~66 files still use `from typing import …` (documented deviation).
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
- **NO open GitLab host allowlist** → default `gitlab.com` only; opt-in via settings/env (SSRF with token).

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
- **NO hardcoded secrets** → env / `.secrets.toml` / `.env` (never commit).

### Build/Testing
- **NO production logic only in tests**.
- **NO real API calls in unit tests**.
- **NO integration tests under `tests/unit/`**.
- **NO interactive git flags** (`-i`) in scripts/hooks.

### Large Files
- Prefer modules **&lt;500 lines** when adding features; extract packages if growing.
- Current production hotspots ≥500: `github/file_processor.py` (595), `parallel/executor.py` (601), `domain/exceptions.py` (580), `services/pr_diff_service.py` (527), `github/diff_generator.py` (517), `tool_registry.py` (496).
- Large tests remain (e.g. auth suite); prefer splitting when editing.

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
- Server: `./start-prdiffer-mcp-server.sh` loads `.env` (tokens + `GITLAB_ALLOWED_HOSTS`).

### Organization
- Dual factories: domain interfaces (`domain/factories/`), infrastructure/application implement.
- VCS registry + `supports_repository()` for multi-provider URLs (GitHub.com + GitLab MR path marker incl. custom hosts).
- Tools registered in `ToolRegistry` (not a separate plugin package; `application/plugins/` is empty reserved path).
- Cache, circuit breaker, and some utils use **flattened modules + package shims** for backward-compatible imports.
- GitHub full-diff pipeline under `infrastructure/github/`; GitLab under `infrastructure/vcs_providers/gitlab_*`.

## COMMANDS
```bash
# Environment
uv sync --group dev     # Install project + dev deps from lockfile
uv run <cmd>            # Run tools in project env
cp .env.example .env    # Tokens + GitLab allowlist template

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
- **VCS**: GitHub (session-isolated full-diff) + GitLab (strict version-pinned full-diff; host allowlist). Registry auto-detects from URL.
- **Custom GitLab**: `GITLAB_ALLOWED_HOSTS=gitlab.com,your.host` + `GITLAB_TOKEN`; MR URLs via `https://host/group/project/-/merge_requests/N`.
- **Package version**: `pyproject.toml` = `0.6.0`; keep `prdiffer/version.py` in sync when releasing.
- **Python**: 3.14.3+ required; local pin `.python-version` = 3.14.6.
- **AGENTS.md coverage**: 44 files (root + layer/package docs under `prdiffer/`, `tests/`, `scripts/`).
- **Empty reserved dirs**: `application/plugins/`, `application/services/`, `application/interfaces/`, `infrastructure/interfaces/` (docs only / placeholders).
- **Analyzer layers**: Application 21, Domain 42, Infrastructure 80 modules (146 total in `prdiffer/`).
