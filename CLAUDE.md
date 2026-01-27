# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Current Version:** 0.4.9

# OpenSpec Instructions

For planning/proposals, see `@/openspec/AGENTS.md`.

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
uv install              # Install dependencies (Python 3.14+)
uv install --dev        # Install development dependencies

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

## Architecture Overview

Clean Architecture with three main layers:

### Domain Layer (`prdiffer/domain/`)
Core business objects and interfaces: `FilePatchInfo`, `PRDiff`, `GetPRDiffUseCase`, repository/service interfaces, VCS provider registry.

### Infrastructure Layer (`prdiffer/infrastructure/`)
Concrete implementations: GitHub/GitLab VCS providers, DI container, GitHub components (api_client, file_processor, diff_generator), security (InputValidator), async infrastructure (RequestCoalescingService, AsyncParallelExecutor), caching, logging.

### Application Layer (`prdiffer/application/`)
MCP server, plugin system, and components: AuthenticationMiddleware, RateLimiter, MetricsTracker, HealthMonitor, PROperationHandler.

## Key Technical Details

### Settings Configuration
Uses `settings.toml` with Dynaconf. Key groups: GitHub API (rate_limit, timeout, retries), Smart Retry (404/403/500 handling), Circuit Breaker, Parallel Diff Processing, File Filtering.

### PR Diff Processing Pipeline
1. File Retrieval via PyGithub API
2. File Filtering (ignore patterns, valid extensions)
3. Content Loading (limited by max_files_allowed)
4. Patch Generation (full-file unified diffs)
5. Extended Diff Creation with headers

### Async Infrastructure
Uses **anyio** for backend-agnostic async operations. Key primitives: `anyio.Semaphore` (concurrency control), `anyio.Lock` (mutual exclusion), `anyio.Event` (signaling), `anyio.create_task_group()` (structured concurrency), `anyio.fail_after()` (timeouts).

Two parallel execution strategies:
- **AsyncParallelExecutor** (preferred): Native async with anyio task groups
- **ParallelExecutor** (legacy): Thread-based for blocking operations

### Transport Configuration
Modes: `stdio` (default), `http`, `sse`, `streamable-http`

### Security and Input Validation
Comprehensive validation via `InputValidator`: URL validation, pattern detection (command injection, path traversal, SQL injection), repository validation, string sanitization, safe logging.

**Authentication is enabled by default** for production. Disable with `export MCP_AUTH_ENABLED=false`.

API key configuration:
```bash
export MCP_API_KEYS="key1,key2"
export MCP_ADMIN_API_KEY="admin-key"
```

### Error Handling
Structured error codes: E1xxx (validation), E2xxx (auth), E3xxx (rate limiting), E4xxx (not found), E5xxx (server errors).

Exception hierarchy: 27 exception types across Authentication, Rate Limiting, Validation, GitHub API, Cache, Configuration, Processing, Resource, and Security categories.

### Caching System
Commit-based caching with automatic invalidation. Cache keys use MD5 hashing (configurable). Cache data includes commit_sha, PRDiff, and timestamp.

### VCS Provider System
Multi-provider abstraction with `VCSProviderRegistry` for auto-detection. GitHub and GitLab implementations included; extensible for other providers.

### Dependency Injection
`ServiceContainer` manages service lifecycles (singleton/transient). `ServiceFactory` provides centralized service creation. All classes support optional DI parameters with backward compatibility.

## Feature Status

### Fully Implemented ✅
PR Diff Retrieval, Multi-Provider VCS Support, Commit-Based Caching, File Filtering, Authentication (SHA-256), Rate Limiting (100 req/min), Health Monitoring, Metrics Tracking, Input Validation, Retry Logic, Circuit Breaker, Async Parallel Processing, Thread Safety, Plugin System, Dependency Injection, VCS Provider Registry.

### Planned Features 🚧
See `ROADMAP.md` for details. Planned: PR operations (describe, approve, review, changelog), runtime admin features (API key management, auth status query), configuration utilities (circuit breaker control, adaptive retry), monitoring & debugging (health status, client info, metrics reset).

### Runtime Management Features (Implemented but not exposed via API)
Methods in `prdiffer/application/components/authentication.py` for runtime API key management and JWT verification. Await admin API/CLI interface.

## Documentation References
- `ROADMAP.md` - Detailed planning with version targets
- `COMPREHENSIVE-DEVELOPMENT-PLAN.md` - Implementation tasks and status
- `openspec/AGENTS.md` - Architecture guides
- `.reports/dead-code-analysis.md` - Unused code analysis

## OpenSpec System

Spec-driven development workflow.

### Directory Structure
```
openspec/
├── AGENTS.md          # AI assistant instructions
├── project.md         # Project conventions
├── specs/             # Current truth (what IS built)
├── changes/           # Proposals (what SHOULD change)
│   └── archive/       # Completed changes
```

### Workflow
1. Create proposal for new features/breaking changes
2. Implement tasks from tasks.md
3. Archive changes after deployment

### Commands
```bash
openspec list                  # List active changes
openspec list --specs          # List specifications
openspec show [item]           # Display change or spec
openspec validate [item]       # Validate
openspec archive <change-id>   # Archive after deployment
```

### Spec Format
Scenarios use `#### Scenario:` (4 hashes). Delta operations: `## ADDED`, `## MODIFIED`, `## REMOVED`, `## RENAMED`.

## Code Search with mgrep

Semantic code search with natural-language queries.

```bash
mgrep "where do we set up auth?" src/lib
mgrep -m 25 "store schema"  # Limit results
mgrep -a "What parsers available?"  # Generate AI answer
```

**Options**: `-m <count>` (max results), `-c` (show content), `-a` (AI answer), `-s` (sync files), `--no-rerank` (disable reranking).
