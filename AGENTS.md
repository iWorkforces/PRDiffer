# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-27T00:30:26Z
**Commit:** d92fa0b1 (Add `approve_pr` mcp tool)
**Branch:** upstream
**Version:** 0.4.9

## OVERVIEW
Python 3.14+ MCP server for GitHub PR diff analysis with Clean Architecture (Domain → Application → Infrastructure). FastMCP framework, Pydantic v2, anyio async.

## STRUCTURE
```
PRDifferMCP/
├── prdiffer/
│   ├── domain/           # Pure business logic (entities, interfaces, VCS registry)
│   ├── infrastructure/   # External integrations (GitHub, caching, DI, VCS providers)
│   └── application/     # MCP server, components, plugin system
├── tests/               # Unit/integration (pytest, 863+ tests, ~70% coverage)
├── openspec/            # Spec-driven development workflow
└── settings.toml        # Dynaconf configuration
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add VCS provider** | `prdiffer/domain/vcs_provider_registry.py`, `prdiffer/infrastructure/vcs_providers/` | Implement VCSDiffRepositoryInterface, register in registry |
| **Add MCP tool** | `prdiffer/application/plugins/` | Extend MCPToolPlugin interface, register in PluginManager |
| **Modify DI** | `prdiffer/infrastructure/di_container.py`, `prdiffer/infrastructure/service_factory.py` | Use ServiceContainer for singletons, ServiceFactory for creation |
| **Add exception** | `prdiffer/domain/exceptions.py`, `prdiffer/domain/errors.py` | Follow E{category}{number}_{NAME} format |
| **Config changes** | `settings.toml` | Dynaconf groups: mcp, github, smart_retry, circuit_breaker |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| PRDiff | Entity | `prdiffer/domain/entities/` | Core diff model |
| VCSDiffRepositoryInterface | Interface | `prdiffer/domain/interfaces/vcs_provider.py` | VCS provider contract |
| VCSProviderRegistry | Registry | `prdiffer/domain/vcs_provider_registry.py` | Provider auto-detection |
| ServiceContainer | DI | `prdiffer/infrastructure/di_container.py` | Singleton/transient services |
| PluginManager | Plugin | `prdiffer/application/plugin_manager.py` | Tool plugin discovery |
| InputValidator | Security | `prdiffer/infrastructure/security/` | Comprehensive validation |

## CONVENTIONS

### Clean Architecture
- **Domain**: Pure Python, no external deps. Define interfaces only.
- **Infrastructure**: Implements domain interfaces. Handles I/O/network.
- **Application**: Orchestrates. Imports from both layers.
- **Layer direction**: Only outer layers import inner layers (Application → Infrastructure → Domain).

### Dependency Injection
- Constructor injection preferred. Optional DI params with singleton fallbacks.
- `container=None` pattern for testability.
- ServiceContainer for singletons, ServiceFactory for creation.

### Async
- **anyio** for backend-agnostic async. Native async preferred over threading.
- AsyncParallelExecutor (anyio task groups) > ParallelExecutor (threads).
- Primitives: Semaphore (concurrency), Lock (exclusion), Event (signaling), create_task_group() (structured concurrency).

### Configuration
- **Dynaconf** via settings.toml. Manual caching (no @lru_cache) due to hashability.
- Environment vars: GITHUB_TOKEN, MCP_AUTH_ENABLED, MCP_API_KEYS.

### Error Codes
- Format: `E{category}{number}_{NAME}` (e.g., E1001_VALIDATION_ERROR)
- Categories: 1xxx validation, 2xxx auth, 3xxx rate limiting, 4xxx not found, 5xxx server errors.

### Testing
- **pytest** with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.security`, `@pytest.mark.thread_safety`.
- Coverage: Overall >80%, Domain >90%, Infrastructure >75%, Application >85%.

## ANTI-PATTERNS (THIS PROJECT)

- **NO imports from outer layers in domain** → Domain must stay pure.
- **NO direct PyGithub in application** → Use infrastructure services.
- **NO @lru_cache on settings** → Use manual caching (Dynaconf unhashable).
- **NO async/await mixed with blocking I/O** → Use AsyncParallelExecutor for non-blocking calls.
- **NO type error suppression** → Never use `as any`, `@ts-ignore`, `@type: ignore`.
- **NO empty catch blocks** → Always log or handle exceptions.

## UNIQUE STYLES

- **VCS Provider Registry**: Auto-detection from URL patterns. Extensible for GitHub/GitLab/Bitbucket.
- **Plugin System**: MCPToolPlugin interface for modular tools. PluginManager discovers and executes.
- **Commit-Based Caching**: MD5 hash keys, auto-invalidate on commit changes.
- **Full-File Diff**: Uses difflib.SequenceMatcher, not just hunks.
- **Security**: InputValidator detects injection patterns (command, path traversal, SQL), sanitizes logs.

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
