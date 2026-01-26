# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Current Version:** 0.4.9

# OpenSpec Instructions

For planning/proposals, see `@/openspec/AGENTS.md`.

## Key Commands

### Environment Setup
```bash
uv install              # Install dependencies (Python 3.14+)
uv install --dev        # Install development dependencies
```

### Running the Server
```bash
uv run python prdiffer/server.py
TRANSPORT=sse PORT=9102 uv run python prdiffer/server.py
```

### Development Commands
```bash
# Linting
./start-lint.sh --check      # Check only
./start-lint.sh --fix        # Auto-fix
./start-lint.sh --format     # Format code
./start-lint.sh --all        # Complete workflow

# Type Checking
./start-type-check.sh --check
./start-type-check.sh --stats
./start-type-check.sh --watch

# Unit Testing
./start-unittest.sh --run         # All tests
./start-unittest.sh --coverage    # With coverage
./start-unittest.sh --parallel    # Parallel execution
./start-unittest.sh --file <path> # Specific file
./start-unittest.sh --watch       # Watch mode
```

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

## Important Implementation Notes

- **Modular Architecture**: Components implement domain service interfaces for testability
- **Settings Caching**: Manual caching instead of `@lru_cache` due to Dynaconf hashability
- **Full-File Diff Generation**: Uses `difflib.SequenceMatcher` for line-by-line comparison
- **File Processing**: Pattern-based filtering, batch content retrieval, parallel execution, encoding support (UTF-8, iso-8859-1, latin-1, ascii, utf-16)
- **Utility Components**: RetryHandler, PatternMatcher, DiffUtils, CircuitBreaker, APIHealthTracker
- **CacheDecorator**: Method-level caching with TTL, LRU eviction, and unhashable parameter handling

## Test Structure

Comprehensive test suite (50+ files) across unit, integration, and performance layers.

**Test Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.security`, `@pytest.mark.thread_safety`

**Coverage Goals**: Overall >80%, Domain >90%, Infrastructure >75%, Application >85%

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
