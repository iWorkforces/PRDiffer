# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-29T16:01:46Z
**Commit:** 1ac0876
**Branch:** upstream
**Version:** 0.4.9

## OVERVIEW
Python 3.14+ MCP server for GitHub PR diff analysis with Clean Architecture (Domain → Application → Infrastructure). FastMCP framework, Pydantic v2, anyio async.

## STRUCTURE
```
PRDifferMCP/
├── prdiffer/
│   ├── domain/           # Pure business logic (30 files, 6 subdirs)
│   ├── infrastructure/   # External integrations (33 files, 6 subdirs)
│   └── application/     # MCP server, components, plugin system (15 files, 5 subdirs)
├── tests/               # Unit/integration (pytest, 863+ tests, ~70% coverage)
├── docs/                # Documentation (19 files)
├── scripts/              # Helper scripts and git hooks
└── settings.toml        # Dynaconf configuration
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add VCS provider** | `prdiffer/domain/vcs_provider_registry.py`, `prdiffer/infrastructure/vcs_providers/` | Implement VCSDiffRepositoryInterface, register in registry |
| **Add MCP tool** | `prdiffer/application/plugins/` | Extend MCPToolPlugin interface, register in PluginManager |
| **Modify DI** | `prdiffer/infrastructure/di_container.py`, `prdiffer/infrastructure/factories/infrastructure_factory.py` | Use ServiceContainer for singletons, ServiceFactory for creation |
| **Add exception** | `prdiffer/domain/exceptions.py`, `prdiffer/domain/errors.py` | Follow E{category}{number}_{NAME} format |
| **Config changes** | `settings.toml` | Dynaconf groups: mcp, github, smart_retry, circuit_breaker |
| **Retry logic** | `prdiffer/infrastructure/utils/retry_handler.py` | Unified retry with exponential backoff, circuit breaker, context-aware configs |
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
| FastMCPServer | Application | `prdiffer/application/mcp_server.py` | 870-line MCP server orchestrator |
| InputValidator | Security | `prdiffer/infrastructure/security/input_validator.py` | Comprehensive validation with 765 lines |

## CONVENTIONS

### Clean Architecture
- **Domain**: Pure Python, no external deps. Define interfaces only.
- **Infrastructure**: Implements domain interfaces. Handles I/O/network.
- **Application**: Orchestrates. Imports from both layers.
- **Layer direction**: Only outer layers import inner layers (Application → Infrastructure → Domain).
- **Max depth**: 3 levels (intentionally shallow for discoverability).

### Dependency Injection
- Constructor injection preferred. Optional DI params with singleton fallbacks.
- `container=None` pattern for testability.
- ServiceContainer for singletons, ServiceFactory for creation.
- 15+ `get_*()` factory functions for lazy initialization.

### Async
- **anyio** for backend-agnostic async. Native async preferred over threading.
- AsyncParallelExecutor (anyio task groups) > ParallelExecutor (threads).
- Primitives: Semaphore (concurrency), Lock (exclusion), Event (signaling), create_task_group().
- **Dual APIs**: Sync/async versions for critical utilities.

### Configuration
- **Dynaconf** via settings.toml. Manual caching (no @lru_cache) due to hashability.
- Environment vars: GITHUB_TOKEN, MCP_AUTH_ENABLED, MCP_API_KEYS.

### Error Codes
- Format: `E{category}{number}_{NAME}` (e.g., E1001_VALIDATION_ERROR)
- Categories: 1xxx validation, 2xxx auth, 3xxx rate limiting, 4xxx not found, 5xxx server errors.

### Testing
- **pytest** with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.security`, `@pytest.mark.thread_safety`.
- Coverage: Overall >80%, Domain >90%, Infrastructure >75%, Application >85%.
- Test structure: tests/unit/domain, tests/unit/infrastructure, tests/unit/application, tests/integration.

## ANTI-PATTERNS (THIS PROJECT)

- **NO imports from outer layers in domain** → Domain must stay pure.
- **NO direct PyGithub in application** → Use infrastructure services.
- **NO @lru_cache on settings** → Use manual caching (Dynaconf unhashable).
- **NO async/await mixed with blocking I/O** → Use AsyncParallelExecutor for non-blocking calls.
- **NO type error suppression** → Never use `as any`, `@ts-ignore`, `@type: ignore`.
- **NO empty catch blocks** → Always log or handle exceptions.
- **NEVER use unverified JWT parsing** → Only for metadata extraction, not auth decisions.
- **Never retry 404s for file content** → Likely added/removed files.

## UNIQUE STYLES

- **VCS Provider Registry**: Auto-detection from URL patterns. Extensible for GitHub/GitLab.
- **Plugin System**: MCPToolPlugin interface for modular tools. PluginManager discovers and executes.
- **Commit-Based Caching**: MD5 hash keys, auto-invalidate on commit changes.
- **Full-File Diff**: Uses difflib.SequenceMatcher, not just hunks.
- **Security**: InputValidator detects injection patterns (command, path traversal, SQL), sanitizes logs.
- **Three-Tier Resilience**: Retry → Circuit Breaker → API Health Tracker (optional advanced features).
- **Dual Async/Sync APIs**: UnifiedRetryHandler, CircuitBreaker provide both versions.
- **Request Coalescing**: Deduplicates concurrent requests for same resource with anyio primitives.
- **ETag Conditional Requests**: HTTP 304 handling to reduce bandwidth.
- **Layer-Specific Factories**: InfrastructureFactory for external services, get_*() functions for internal services.

## COMMANDS
```bash
# Environment setup
uv install              # Install dependencies
uv install --dev        # Install dev deps

# Linting
./start-lint.sh --check      # Check only
./start-lint.sh --fix        # Auto-fix
./start-lint.sh --format     # Format code
./start-lint.sh --all        # Complete workflow

# Type checking
./start-type-check.sh --check
./start-type-check.sh --stats

# Unit testing
./start-unittest.sh --run         # All tests
./start-unittest.sh --coverage    # With coverage
./start-unittest.sh --parallel    # Parallel execution

# Server
uv run python prdiffer/server.py
TRANSPORT=sse PORT=9102 uv run python prdiffer/server.py
```

## NOTES

- **Authentication enabled by default** (production). Disable: `export MCP_AUTH_ENABLED=false`.
- **VCS provider auto-detection** from URL. Implement new providers: VCSDiffRepositoryInterface + register in VCSProviderRegistry.
- **Plugin registration** requires implementing MCPToolPlugin and registering in PluginManager.
- **Retry logic**: 404/403/500 with smart retry, circuit breaker, exponential backoff.
- **File filtering**: Pattern-based ignores, extension allowlist, max_files_allowed limit.
- **Test markers for filtering**: `-m unit`, `-m integration`, `-m slow`, `-m security`.
- **Complex files**: 25 files >500 lines, most in infrastructure (retry_handler.py: 971 lines).
- **Thread safety**: RLock for sync, anyio.Lock for async, double-check locking patterns.
- **Maximum directory depth**: 3 levels (prdiffer/{layer}/{package}/{module}.py).
