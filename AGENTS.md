# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-30T14:05:00Z
**Commit:** 8fcfc9b
**Branch:** upstream
**Version:** 0.5.0

## OVERVIEW
Python 3.14+ MCP server for GitHub PR diff analysis with Clean Architecture (Domain → Application → Infrastructure). FastMCP framework, Pydantic v2, anyio async. 177 Python files, 42K lines, 26 AGENTS.md files.

## STRUCTURE
```
PRDifferMCP/
├── prdiffer/
│   ├── domain/           # Pure business logic (34 files, 7 subdirs, 7 __init__.py)
│   ├── infrastructure/   # External integrations (41 files, 6 subdirs, 6 __init__.py)
│   └── application/     # MCP server, components, plugin system (22 files, 5 subdirs, 5 __init__.py)
├── tests/               # Unit/integration (74 files: 55 unit + 8 integration + 8 perf + 3 phase)
├── docs/                # Documentation (error-codes.md only, gitignored)
├── scripts/              # Helper scripts, git-hooks, analysis tools
└── settings.toml        # Dynaconf configuration (212 lines, 14 groups)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add VCS provider** | `prdiffer/domain/vcs_provider_registry.py`, `prdiffer/infrastructure/vcs_providers/` | Implement VCSDiffRepositoryInterface, register in registry |
| **Add MCP tool** | `prdiffer/application/plugins/` | Extend MCPToolPlugin interface, register in PluginManager |
| **Modify DI** | `prdiffer/infrastructure/di_container.py`, `prdiffer/infrastructure/factories/infrastructure_factory.py` | Use ServiceContainer for singletons, ServiceFactory for creation |
| **Add exception** | `prdiffer/domain/exceptions.py`, `prdiffer/domain/errors.py` | Follow E{category}{number}_{NAME} format |
| **Config changes** | `settings.toml` | Dynaconf groups: mcp, auth, github, cache, diff, security |
| **Retry logic** | `prdiffer/infrastructure/utils/retry_handler.py` | 971-line unified handler with exponential backoff, circuit breaker, context-aware configs |
| **Caching** | `prdiffer/infrastructure/cache_service.py`, `prdiffer/infrastructure/utils/cache_decorator.py` | Commit-based invalidation, LRU eviction, TTL support |
| **Security** | `prdiffer/infrastructure/security/input_validator.py` | Pattern-based injection detection (command, path traversal, SQL) |
| **Async patterns** | `prdiffer/infrastructure/async_parallel_executor.py` | anyio primitives: Semaphore, Lock, Event, task groups |

## CODE MAP
| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|
| PRDiff | Entity | `prdiffer/domain/entities/` | Core diff model |
| FilePatchInfo | Entity | `prdiffer/domain/entities/` | Rich domain model with business logic |
| VCSDiffRepositoryInterface | Interface | `prdiffer/domain/interfaces/vcs_provider.py` | VCS provider contract |
| VCSProviderRegistry | Registry | `prdiffer/domain/vcs_provider_registry.py` | Provider auto-detection from URL |
| ServiceContainer | DI | `prdiffer/infrastructure/di_container.py` | Singleton/transient services |
| UnifiedRetryHandler | Service | `prdiffer/infrastructure/utils/retry_handler.py` | 971-line retry handler with circuit breaker |
| CircuitBreaker | Service | `prdiffer/infrastructure/utils/circuit_breaker.py` | Fault tolerance with state machine |
| AsyncParallelExecutor | Service | `prdiffer/infrastructure/async_parallel_executor.py` | anyio-based parallel execution |
| PluginManager | Plugin | `prdiffer/application/plugin_manager.py` | MCP tool plugin discovery |
| FastMCPServer | Application | `prdiffer/application/mcp_server.py` | 239-line MCP server orchestrator (refactored) |
| ToolRegistry | Application | `prdiffer/application/tool_registry.py` | 581-line MCP tool registration |
| WebhookHandler | Application | `prdiffer/application/webhook_handler.py` | 214-line GitHub webhook processing |
| HealthEndpoints | Application | `prdiffer/application/health_endpoints.py` | 180-line health checks and metrics |
| InputValidator | Security | `prdiffer/infrastructure/security/input_validator.py` | Input validation orchestrator (571 lines, refactored) |
| InjectionDetector | Security | `prdiffer/infrastructure/security/injection_detector.py` | 267-line pattern-based threat detection |
| Sanitizer | Security | `prdiffer/infrastructure/security/sanitizer.py` | 156-line input sanitization |
| LazyLoggerMixin | Utility | `prdiffer/infrastructure/utils/logger_factory.py` | 66-line shared logger initialization pattern |

## CONVENTIONS

### Clean Architecture
- **Domain**: Pure Python, no external deps. Define interfaces only.
- **Infrastructure**: Implements domain interfaces. Handles I/O/network.
- **Application**: Orchestrates. Imports from both layers.
- **Layer direction**: Only outer layers import inner layers (Application → Infrastructure → Domain).
- **Max depth**: 3 levels (intentionally shallow for discoverability).
- **No outer layer imports in domain** → Domain must stay pure.

### Dependency Injection
- Constructor injection preferred. Optional DI params with singleton fallbacks.
- `container=None` pattern for testability.
- ServiceContainer for singletons, ServiceFactory for creation.
- 15+ `get_*()` factory functions for lazy initialization.
- No global state → Use ServiceContainer for singletons.

### Async
- **anyio** for backend-agnostic async. Native async preferred over threading.
- AsyncParallelExecutor (anyio task groups) > ParallelExecutor (threads).
- Primitives: Semaphore (concurrency), Lock (exclusion), Event (signaling), create_task_group().
- **Dual APIs**: Sync/async versions for critical utilities.
- **NO asyncio in tests** → Use anyio primitives (project is anyio-first).

### Configuration
- **Dynaconf** via settings.toml. Manual caching (no @lru_cache) due to hashability.
- Environment vars: GITHUB_TOKEN, MCP_AUTH_ENABLED, MCP_API_KEYS.
- SettingsService with RLock for thread-safe manual caching.
- GitHubConfig frozen dataclass with tuple-based fields (hashable).

### Error Codes
- Format: `E{category}{number}_{NAME}` (e.g., E1001_VALIDATION_ERROR)
- Categories: 1xxx validation, 2xxx auth, 3xxx rate limiting, 4xxx not found, 5xxx server errors.

### Testing
- **pytest** with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.security`, `@pytest.mark.thread_safety`.
- Coverage: Overall >80%, Domain >90%, Infrastructure >75%, Application >85%.
- Test structure: tests/unit/domain, tests/unit/infrastructure, tests/unit/application, tests/integration.
- anyio-first async testing (not asyncio).
- Custom auto-use fixtures for environment setup and singleton reset.

## ANTI-PATTERNS (THIS PROJECT)

### Critical Anti-Patterns
- **NO imports from outer layers in domain** → Domain must stay pure.
- **NO direct PyGithub in application** → Use infrastructure services.
- **NO @lru_cache on settings** → Use manual caching (Dynaconf unhashable).
- **NO async/await mixed with blocking I/O** → Use AsyncParallelExecutor for non-blocking calls.
- **NO type error suppression** → Never use `as any`, `@ts-ignore`, `@type: ignore`.
- **NO empty catch blocks** → Always log or handle exceptions.
- **NO old-style typing imports** → Use built-in types (`list[str]`) instead of `from typing import List`. (Documented but 48 violations exist)
- **NO asyncio in tests** → Use anyio primitives instead (project is anyio-first).
- **NEVER use unverified JWT parsing** → Only for metadata extraction, not auth decisions.
- **Never retry 404s for file content** → Likely added/removed files.

### Architecture Enforcement
- **NO business logic in application** → Domain layer only (components are orchestration).
- **NO PyGithub in plugins** → Use PRDiffService/PROperationHandler.
- **NO static plugin registration** → Use PluginManager or factory.
- **NO plugin state mutation** → Plugins should be stateless or manage state internally.
- **NO synchronous blocking** → All tool execution must be async.
- **NO direct infrastructure calls in components** → Inject via DI.
- **NO bypassing circuit breaker** → Always go through CircuitBreaker for external APIs.

### Security Enforcement
- **NO command injection** → Shell metacharacters, command substitution.
- **NO path traversal** → `..`, `~/`, `/etc/`, `/var/`, `/usr/`, Windows paths.
- **NO SQL injection** → `--`, `/*`, SQL keywords.
- **NO hardcoded secrets** → Use environment variables.

### Build/Testing Anti-Patterns
- **NO production logic in tests** → Tests only.
- **NO test dependencies** → Use fixtures.
- **NO integration tests in unit/ → Use mocks, separate integration/.
- **NO real API calls** → Mock all external dependencies.
- **NO blocking I/O tests** → Use AsyncParallelExecutor patterns.

## UNIQUE STYLES

### Entry Point Patterns
- **Transport-aware output stream redirection**: Send diagnostics to stderr for stdio mode, stdout for other transports (prevents JSON-RPC corruption).
- **Environment variable priority system**: CLI args > existing env vars > defaults (modifies os.environ in-place).
- **Manual sys.path injection**: Allows direct execution without installation (anti-pattern for production, convenient for dev).

### Build/CI Patterns
- **Manual git hook distribution**: Custom `setup-git-hooks.sh` copies hooks from `scripts/git-hooks/` to `.git/hooks/` (version-controlled, team synchronization).
- **Pre-push enforcement**: Type checking + linting before every push (blocks push on failure).
- **Developer tool wrappers**: `start-cc-mmax.sh`, `start-cc-zai.sh`, `start-oc-zai.sh` for Claude Code with environment management.
- **Comprehensive server startup script**: `start-prdiffer-mcp-server.sh` (388 lines) with auto uv installation, PID management, health checks, graceful shutdown.
- **Architecture violation detection**: `scripts/analyze_dependencies.py` uses AST to detect Clean Architecture violations (exits with error code 1).
- **No CI/CD infrastructure**: Manual quality gates only (no GitHub Actions, Makefile, pre-commit).

### Testing Patterns
- **anyio-first async**: Uses `anyio.run()`, `anyio.Lock`, `anyio.Semaphore`, `anyio.create_task_group()` (not asyncio).
- **Generator fixtures**: `mock_github_file()`, `generate_pr_url()`, `generate_diff_content()`, `run_concurrently()` for test data.
- **Thread safety testing**: `run_concurrently` fixture with anyio.Semaphore for concurrency limits.
- **Performance testing**: `tests/performance/test_performance.py` with `time.perf_counter()` for benchmarking.

### Configuration Patterns
- **Manual caching with RLock**: SettingsService uses module-level `_settings_service = None` with RLock for thread-safe caching (no @lru_cache).
- **GitHubConfig frozen dataclass**: Immutable with tuple fields (not lists) for hashability.
- **Security pattern configuration**: Configurable regex patterns in `settings.toml` for injection detection (command, path traversal, SQL).

### Organization Patterns
- **Dual factory pattern**: Domain-level factories (`domain/factories/`) define interfaces, infrastructure implements them.
- **VCS provider registry**: Auto-detection from URL patterns via `supports_repository()` method.
- **Plugin system**: MCPToolPlugin interface with PluginManager discovery and execution.
- **Layer-specific AGENTS.md**: Each layer has own AGENTS.md documenting conventions (26 files total).

## COMMANDS
```bash
# Environment setup
uv install              # Install dependencies
uv install --dev        # Install dev deps

# Linting (custom scripts, no pyproject.toml ruff config)
./start-lint.sh --check      # Check only
./start-lint.sh --fix        # Auto-fix
./start-lint.sh --format     # Format code
./start-lint.sh --all        # Complete workflow (triple-quote replacement, check→fix→format)

# Type checking
./start-type-check.sh --check
./start-type-check.sh --stats

# Unit testing
./start-unittest.sh --run         # All tests
./start-unittest.sh --coverage    # With coverage (HTML+term)
./start-unittest.sh --parallel     # Parallel execution (CPU count workers)
./start-unittest.sh --watch        # Watch mode (pytest-watch)
./start-unittest.sh --file <path>  # Specific file
./start-unittest.sh --pattern <pat> # Match pattern (-k equivalent)

# Server
uv run python prdiffer/server.py
./start-prdiffer-mcp-server.sh  # Comprehensive startup with auto uv, PID mgmt

# Architecture validation
python scripts/analyze_dependencies.py --path prdiffer

# Git hooks
./scripts/setup-git-hooks.sh  # Install version-controlled hooks

# Developer tools
./start-cc-mmax.sh -- <args>  # Claude Code with .env.cc.mmax
./start-cc-zai.sh -- <args>   # Claude Code with .env.cc.zai
./start-oc-zai.sh -- <args>   # OpenCode with .env.oc.zai
```

## NOTES

- **Authentication enabled by default** (production). Disable: `export MCP_AUTH_ENABLED=false`.
- **VCS provider auto-detection** from URL. Implement new providers: VCSDiffRepositoryInterface + register in VCSProviderRegistry.
- **Plugin registration** requires implementing MCPToolPlugin and registering in PluginManager.
- **Retry logic**: 404/403/500 with smart retry, circuit breaker, exponential backoff.
- **File filtering**: Pattern-based ignores, extension allowlist, max_files_allowed limit.
- **Test markers for filtering**: `-m unit`, `-m integration`, `-m slow`, `-m security`.
- **Complex files**: 32 files >500 lines, most in infrastructure (retry_handler.py: 971 lines).
- **Thread safety**: RLock for sync, anyio.Lock for async, double-check locking patterns.
- **Maximum directory depth**: 3 levels (prdiffer/{layer}/{package}/{module}.py).
- **No CI/CD infrastructure**: Manual quality gates only; no GitHub Actions workflows exist.
- **Type hint deviation**: Project uses old-style typing imports (`from typing import List`) instead of Python 3.14+ built-ins.
- **Custom git hooks**: Pre-push hook enforces type checking + linting (bypass with `--no-verify`).
- **Manual caching pattern**: SettingsService with RLock due to Dynaconf unhashability (no @lru_cache).
