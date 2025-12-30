# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

## Project Overview

CCPRAgents is an MCP (Model Context Protocol) server that provides GitHub PR diff analysis capabilities. It's built using FastMCP framework and follows Clean Architecture principles with domain-driven design.

## Key Commands

### Environment Setup
```bash
# Install dependencies (requires Python 3.14+)
uv install

# Install development dependencies
uv install --dev
```

### Running the Server
```bash
# Run MCP server (default HTTP transport on port 9102)
uv run python ccpragents/server.py

# Run with different transport/port via environment variables
TRANSPORT=sse PORT=9102 uv run python ccpragents/server.py
```

### Development Commands
```bash
# Lint code (check only)
./start-lint.sh --check

# Lint and auto-fix issues
./start-lint.sh --fix

# Format code
./start-lint.sh --format

# Run complete linting workflow (check, fix, format)
./start-lint.sh --all

# Show linting statistics
./start-lint.sh --stats
```

### Type Checking
```bash
# Run type checking with ty
./start-type-check.sh --check

# Run with detailed statistics
./start-type-check.sh --stats

# Run in watch mode (re-check on file changes)
./start-type-check.sh --watch

# Show ty configuration
./start-type-check.sh --config
```

### Unit Testing
```bash
# Run all tests
./start-unittest.sh --run

# Run tests with coverage analysis
./start-unittest.sh --coverage

# Run tests in parallel (faster)
./start-unittest.sh --parallel

# Run specific test file
./start-unittest.sh --file tests/test_validator.py

# Run tests matching pattern
./start-unittest.sh --pattern validator

# Watch mode (re-run on changes)
./start-unittest.sh --watch

# Show test statistics
./start-unittest.sh --stats
```

### Integration Testing
```bash
# Run basic MCP server test
uv run python tests/test_mcp_server.py
```

## Architecture Overview

The codebase follows Clean Architecture with these layers:

### Domain Layer (`ccpragents/domain/`)
- **Entities**: Core business objects
  - `FilePatchInfo`: File change representation with diff and metadata
  - `PRDiff`: PR model with commit messages and diff content
- **Use Cases**: Business logic orchestration
  - `GetPRDiffUseCase`: Fetches and caches PR diff data
- **Repository Interfaces**: Abstract data access contracts
  - `PRDiffRepositoryInterface`: Contract for PR diff retrieval
- **Service Interfaces** (`domain/services/`): Abstract service contracts
  - `CacheServiceInterface`: Caching abstraction with commit-based invalidation
  - `SettingsServiceInterface`: Configuration management abstraction
  - `LoggerServiceInterface`: Structured logging abstraction
  - `RepositoryCacheServiceInterface`: Repository instance caching
  - `DiffServiceInterface`: Diff generation and manipulation
  - `GitHubAPIServiceInterface`: GitHub API operations
  - `PatternMatchingServiceInterface`: File pattern matching
  - `RetryServiceInterface`: Retry logic with exponential backoff
  - `PRDiffServiceInterface`: PR diff operations abstraction
- **Factory Interfaces** (`domain/factories/`): Dependency injection abstractions
  - `InfrastructureFactoryInterface`: Abstract factory for creating infrastructure services

### Infrastructure Layer (`ccpragents/infrastructure/`)

- **GitHub Integration**:
  - `GitHubPRDiffRepository`: PyGithub implementation of `PRDiffRepositoryInterface`
  - **GitHub Components** (`github/`):
    - `api_client`: GitHub API client wrapper
    - `file_processor`: File filtering and validation
    - `diff_generator`: Unified diff generation
    - `parallel_executor`: Concurrent file processing
- **Security Components** (`security/`):
  - `InputValidator`: Comprehensive input validation and sanitization
    - SQL injection prevention
    - Command injection prevention
    - Path traversal prevention
    - XSS attack prevention
    - GitHub URL validation with security checks
    - Repository identifier validation
    - Token format validation
    - User ID validation
    - Safe logging sanitization
- **Utility Components** (`utils/`):
  - `retry_handler`: Exponential backoff with jitter
  - `pattern_matcher`: File pattern matching with regex
  - `diff_utils`: Core diff operations
  - `circuit_breaker`: Failure prevention pattern
  - `api_health_tracker`: API performance monitoring
- **Services**:
  - `SettingsService`: Dynaconf-based configuration with manual caching
  - `CacheService`: In-memory commit-based caching
  - `RepositoryCacheService`: Repository instance caching
  - `RequestCoalescingService`: Deduplicates concurrent requests for same resources
  - `AsyncParallelExecutor`: Native async parallel processing using anyio task groups
- **Async Infrastructure**:
  - `RequestCoalescingService` (`request_coalescing.py`):
    - Prevents duplicate API calls when multiple concurrent requests arrive for same resource
    - Uses anyio primitives (Lock, Event) for thread-safe request coalescing
    - Timeout protection (configurable, default 30s)
    - Waiter tracking and statistics
    - Atomic state management with proper cleanup
  - `AsyncParallelExecutor` (`async_parallel_executor.py`):
    - Native async parallel processing using anyio task groups instead of ThreadPoolExecutor
    - Multiple error handling strategies: IGNORE, RAISE, COLLECT, CONTINUE
    - BatchResult dataclass for tracking successful/failed operations
    - Execution modes: execute_batch, execute_batch_with_context, execute_mapped_batch, execute_with_progress
    - Semaphore-based concurrency control with configurable limits
    - Better performance than thread-based approach for I/O-bound operations
- **Logging** (`logging/`):
  - `ConsoleLogger`: Structured console output with ANSI colors
- **Factory Implementation** (`factories/`):
  - `InfrastructureFactory`: Concrete implementation of `InfrastructureFactoryInterface`
  - Creates all infrastructure service instances with proper dependency injection
  - Provides singleton access for shared services (settings, logger, cache)
- **Service Implementations** (`services/`):
  - `GitHubPRDiffService`: Concrete implementation of `PRDiffServiceInterface`
  - Provides PR diff operations using GitHub API with graceful error handling
  - Orchestrates diff generation workflow with DiffGenerator and FileProcessor

### Application Layer (`ccpragents/application/`)

- **MCP Server** (`mcp_server.py`):
  - FastMCP server exposing `get_pr_diff` tool
  - Tool registration and request handling
  - Dependency injection orchestration
- **Components** (`components/`):
  - `URLValidator`: GitHub URL parsing and validation
  - `RateLimiter`: Request rate limiting
  - `MetricsTracker`: Performance metrics collection
  - `PROperationHandler`: PR operations coordination
  - `HealthMonitor`: Server health checks
  - `ServerConfiguration`: Runtime configuration
- **Factory** (`factory.py`):
  - `create_mcp_server`: Component wiring and injection
- **Interfaces** (`interfaces/`):
  - Protocol definitions for component contracts

### Interface Layer

- **Server Entry Point**: `ccpragents/server.py` - main server launcher with dependency initialization

## Key Technical Details

### Settings Configuration

- Uses `settings.toml` with Dynaconf for configuration management (supports environment-specific overrides via `[development]`, `[production]`, `[testing]` sections if needed)
- Settings service implements manual caching instead of `@lru_cache` due to Dynaconf object hashability issues
- GitHub settings include file filtering (`ignore_patterns`, `valid_extensions`) stored as tuples for hashability

#### Key Settings Groups

**GitHub API Settings**:
```toml
github.rate_limit = 5000
github.timeout = 30
github.max_retries = 3
github.retry_delay = 1
```

**Smart Retry Settings** (NEW):
```toml
github.retry_on_404 = false   # Don't retry 404 errors (file not found)
github.retry_on_403 = true    # Retry 403 errors (might be rate limiting)
github.retry_on_500 = true    # Retry 5xx server errors
github.retry_log_level = "DEBUG"
github.permanent_failure_log_level = "INFO"
```

**Circuit Breaker and Adaptive Retry** (NEW):
```toml
github.circuit_breaker_enabled = true
github.circuit_breaker_failure_threshold = 5
github.circuit_breaker_timeout = 60
github.adaptive_retry_enabled = true
github.max_adaptive_delay = 30
github.api_health_tracking = true
github.context_aware_retry = true
```

**Parallel Diff Processing** (NEW):
```toml
github.diff_parallel_enabled = true
github.diff_parallel_threshold = 3    # Minimum files to trigger parallel processing
github.diff_max_workers = 4           # Maximum worker threads
github.diff_worker_timeout = 30.0     # Timeout per file in seconds
```

**File Filtering**:
```toml
github.ignore_patterns = ["*.lock", "node_modules/", "dist/", "build/"]
github.valid_extensions = [".py", ".js", ".ts", ".md", ".yml"]
```

### PR Diff Processing Pipeline

1. **File Retrieval**: Gets PR files via PyGithub API
2. **File Filtering**: Applies ignore patterns and valid extensions from settings
3. **Content Loading**: Fetches full file content for base and head commits (limited by `max_files_allowed`)
4. **Patch Generation**: Creates full-file unified diffs using `_build_full_file_patch()`
5. **Extended Diff Creation**: Formats output with file headers and full context

### GitHub API Integration

- **Modular Architecture**: Components split into `api_client`, `file_processor`, `diff_generator`, and `parallel_executor`
- **Retry Logic**: Configurable exponential backoff with jitter via `RetryHandler` utility
- **Pattern Matching**: Advanced file filtering using `PatternMatcher` with pre-compiled regex patterns
- **Diff Generation**: Full-file context diffs using `DiffUtils` with multiple encoding support
- **Authentication**: Handles authentication via parameters or `GITHUB_TOKEN` environment variable
- **Merge Base Handling**: Uses merge base commits for accurate diff comparison (handles parallel merges)

### Async Infrastructure

The project uses **anyio** as the async compatibility layer, providing backend-agnostic async operations:

**Migration Note**: The codebase was migrated from `asyncio` to `anyio` for better abstraction and compatibility with multiple async backends (asyncio, trio, etc.)

#### Anyio Primitives Usage

- **Async Framework**: Uses `anyio` instead of raw `asyncio` for better portability and cleaner APIs
- **Concurrency Primitives**:
  - `anyio.Semaphore`: Controls concurrent operations with configurable limits
    - Used in `AsyncParallelExecutor` for concurrency control
    - Example: `self._semaphore = anyio.Semaphore(max_concurrent)`
  - `anyio.Lock`: Provides mutual exclusion for shared resources
    - Used in `RequestCoalescingService` for atomic state updates
    - Example: `async with self._lock: ...`
  - `anyio.Event`: Enables async event signaling between tasks
    - Used in request coalescing for result notification
    - Example: `event.set()` and `await event.wait()`
  - `anyio.create_task_group()`: Manages parallel task execution with structured concurrency
    - Used in `AsyncParallelExecutor.execute_batch()` for parallel processing
    - Example: `async with anyio.create_task_group() as tg: tg.start_soon(task)`
- **Timeout Handling**: Uses `anyio.fail_after()` context manager for timeout protection
  - Example: `with anyio.fail_after(timeout): result = await operation()`
  - Raises `TimeoutError` when timeout expires

#### Request Coalescing

- **Purpose**: Prevents duplicate API calls when multiple concurrent requests arrive for the same resource
- **Implementation**: `RequestCoalescingService` uses anyio primitives for thread-safe deduplication
- **Key Features**:
  - Atomic state management with `anyio.Lock`
  - Result sharing via `anyio.Event`
  - Timeout protection (configurable, default 30s)
  - Waiter counting and statistics
  - Proper cleanup on success, failure, and timeout
- **Usage Pattern**:
  ```python
  result = await coalescing_service.coalesce(
      key="owner/repo/pr/123",
      fetch_func=lambda: fetch_from_api(),
      timeout=30.0
  )
  ```

#### Parallel Execution Strategies

The project provides **both** thread-based and async-based parallel execution:

1. **AsyncParallelExecutor** (Preferred for async operations):
   - Native async using anyio task groups
   - Better performance for I/O-bound operations
   - Multiple error handling strategies
   - Semaphore-based concurrency control
   - Execution modes: batch, context-based, mapped, with progress

2. **ParallelExecutor** (Legacy, thread-based):
   - ThreadPoolExecutor for synchronous operations
   - Used in `github/parallel_executor.py`
   - Suitable for CPU-bound or blocking operations

#### Testing Compatibility

- **pytest-asyncio**: Compatible with pytest async testing
- **Backend Selection**: anyio uses asyncio backend by default
- **Mock Support**: Easy to mock anyio primitives for testing
- **Deterministic Testing**: Structured concurrency aids testing

#### Additional Async Features

- **Rate Limiting**: Implements rate limiting and timeout configurations with circuit breaker pattern
- **API Health Tracking**: Monitors API performance and error rates
- **Graceful Shutdown**: Proper cleanup of async resources
- **Supports both authenticated and anonymous access**

### Transport Configuration

The MCP server supports multiple transport modes configured in `settings.toml`:

- `stdio`: Standard input/output (default for MCP clients)
- `http`: HTTP server mode
- `sse`: Server-sent events
- `streamable-http`: FastMCP streamable HTTP

### Security and Input Validation

The MCP server implements comprehensive security validation through the `InputValidator` class integrated into `FastMCPServer`:

**Input Validation Features**:
- **URL Validation**: GitHub PR URLs are validated against strict patterns with length limits (max 2000 chars)
- **Pattern Detection**: Blocks suspicious patterns including:
  - Command injection: Shell metacharacters (`;&|`$`), command substitution (`$(`, backticks)
  - Path traversal: Parent directory references (`..`), system directories (`/etc/`, `/var/`, `/usr/`)
  - SQL injection: SQL comments (`--`, `#`, `/* */`), SQL keywords (union, select, insert, etc.)
- **Repository Validation**: Owner and repo names validated against GitHub's naming rules
  - Owner: Max 39 chars, alphanumeric with hyphens/underscores
  - Repo: Max 100 chars, alphanumeric with hyphens/underscores/dots
- **PR Number Validation**: Ensures positive integers with reasonable upper limit (max 1,000,000)
- **String Sanitization**: Removes control characters, checks for null bytes, enforces length limits
- **Safe Logging**: Sanitizes values before logging to prevent log injection attacks

**Security Exceptions**:
- `InvalidURLError`: Malformed or suspicious URLs
- `InvalidRepositoryError`: Invalid repository identifiers
- `InvalidPRNumberError`: Invalid PR numbers
- `InputSanitizationError`: General input validation failures
- `SuspiciousOperationError`: Detected security threats

**Implementation in FastMCPServer** (mcp_server.py):
1. `InputValidator` initialized at line 84
2. URL validation via `validate_github_url()` at line 153
3. Parameter sanitization in `get_pr_diff` tool at lines 222-232
4. Security exception handling at lines 290-314
5. Safe logging with `sanitize_for_logging()` at lines 309, 329

### Error Handling Patterns

- **Security Validation**: All user inputs validated through `InputValidator` before processing
  - Security exceptions (InvalidURLError, SuspiciousOperationError, etc.) caught and logged with sanitized values
  - Failed requests tracked in metrics for security monitoring
- **Graceful Degradation**: Settings service falls back gracefully when cache keys are unhashable
- **API Error Handling**: GitHub API errors return empty strings rather than failing
- **Retry Strategies**: Configurable exponential backoff with jitter for transient failures
- **Circuit Breaker**: Prevents cascading failures by temporarily disabling failing operations
- **Content Decoding**: File content decoding attempts multiple encodings (UTF-8, iso-8859-1, latin-1, ascii, utf-16)
- **Health Monitoring**: API health tracking to detect and respond to performance degradation
- **Safe Error Logging**: All error logs use `sanitize_for_logging()` to prevent log injection

### Caching System

- **Commit-Based Caching**: PR diff data is cached using the latest commit SHA as cache key
- **Automatic Invalidation**: Cache is automatically invalidated when new commits are pushed to the PR
- **Memory Cache**: In-memory caching with commit SHA tracking for freshness
- **Cache Service**: Singleton `CacheService` with commit-based invalidation logic
- **Key Hashing**: MD5-based cache key hashing to reduce memory usage for long repository names (configurable)

**Cache Key Structure**:

- **Original Format**: `"owner/repo/pr/number"` (human-readable, used by external API)
- **Internal Storage**: MD5 hash (32 hex chars) when hashing is enabled
- **Reverse Mapping**: Optional hash→original mapping for debugging and stats

**Cache Key Hashing Configuration** (in `settings.toml`):

```toml
cache.use_hashed_keys = true           # Enable/disable hashing (default: true)
cache.hash_algorithm = "md5"            # Hash algorithm: md5, sha256
cache.store_key_mapping = true          # Store reverse mapping for debugging
```

**Hashing Behavior**:

- **Enabled by default**: All environments use hashed keys for memory efficiency
- **Dual logging**: Both original key and hash are logged for debugging visibility
- **Reverse mapping**: Original keys retrievable via `get_stats()` when mapping is enabled

**Cache Data**: `{"commit_sha": str, "data": PRDiff, "timestamp": float}`

**Cache Flow**:

1. On first request: Fetch data from GitHub, cache with current commit SHA
2. On subsequent requests: Check current commit SHA vs cached SHA
3. If SHAs match: Return cached data (cache hit)
4. If SHAs differ: Fetch fresh data and update cache (cache miss)

**Log Output Example** (with hashing enabled):

```
Cache set [cache_key=karcher-digital/iotc-device-management/pr/163 hash=a7b3c4d5... commit_sha=919da4e...]
```

**Caching is Automatic**: Caching is always enabled and uses commit-based invalidation to ensure fresh data is returned when PRs change.

## Important Implementation Notes

### Modular Architecture
- **Component Extraction**: Original `GitHubPRDiffRepository` (972 lines) refactored into modular components (~200 lines main class)
- **Single Responsibility**: Each component focuses on specific functionality (API client, file processing, diff generation, parallel execution)
- **Interface Compliance**: All components implement domain service interfaces for testability
- **Dependency Injection**: Components use dependency injection for loose coupling

### Caching System
The settings service uses manual caching instead of `@lru_cache` because:
- Dynaconf objects are not hashable
- Lists in configuration are converted to tuples for hashability
- Cache keys handle list-to-tuple conversion in `get()` method

### Full-File Diff Generation
- `_build_full_file_patch()` generates complete file context diffs
- Uses `difflib.SequenceMatcher` for line-by-line comparison
- Method signature fixed from static to instance method for proper `self._build_full_file_patch()` calls
- Output format includes blank line after file header for proper formatting

### File Content Processing
- **Pattern-Based Filtering**: Uses `PatternMatcher` with pre-compiled regex patterns for efficient file validation
- **Batch Processing**: Bulk content retrieval for better API efficiency
- **Parallel Execution**: Thread pool processing for concurrent file operations
- **Content Limiting**: Loads full file content only up to `max_files_allowed` setting (default: 50)
- **Graceful Degradation**: Falls back to patch-only mode for large PRs to avoid rate limiting
- **Encoding Support**: Handles binary files gracefully with multiple encoding attempts (UTF-8, iso-8859-1, latin-1, ascii, utf-16)

### Utility Components
- **RetryHandler**: Configurable exponential backoff with jitter and rate limit detection
- **PatternMatcher**: Efficient file filtering with wildcard support and pre-compiled regex
- **DiffUtils**: Core diff generation with encoding detection and patch extension
- **CircuitBreaker**: Prevents cascading failures by temporarily disabling failing operations
- **APIHealthTracker**: Monitors API performance metrics and error rates
- **CacheDecorator** (`utils/cache_decorator.py`): Method-level caching utility
  - **CachingMixin**: Base class providing caching capabilities to any class
    - Handles unhashable parameters (lists, dicts, sets) through conversion
    - TTL (time-to-live) support with automatic expiration
    - LRU (Least Recently Used) eviction with configurable size limits
    - Cache statistics tracking (hits, misses, hit rate)
    - Thread-safe with proper cleanup
  - **@cached_method** decorator: Caches method results with TTL support
    - Automatic conversion of unhashable types to hashable forms
    - Configurable TTL per method
    - Optional key prefix for cache namespacing
    - Cache invalidation support
  - **@conditional_cache** decorator: Caches based on condition function
    - Only cache results that meet specific criteria
    - Example: Cache only non-None results
  - **Use Cases**:
    - Expensive computations with complex parameters
    - API responses that don't change frequently
    - Settings/configuration values with unhashable data
    - Methods that receive lists, dicts, or other mutable types

### Security Components
- **InputValidator**: Comprehensive input validation and sanitization (infrastructure/security/input_validator.py)
  - **URL Validation**: Validates GitHub PR URLs with strict pattern matching and length limits
  - **Suspicious Pattern Detection**: Blocks command injection, path traversal, and SQL injection attempts
  - **Repository Validation**: Enforces GitHub naming conventions for owners and repos
  - **String Sanitization**: Removes control characters, null bytes, and enforces length constraints
  - **Token Validation**: Validates authentication token format (20-500 chars, alphanumeric)
  - **User ID Validation**: Validates user identifiers (max 100 chars, alphanumeric with @.-_)
  - **Safe Logging**: Sanitizes values for secure logging (max 200 chars, printable chars only)
  - **Convenience Functions**: Module-level functions (validate_github_url, sanitize_string, etc.)
- **Integration**: Integrated into `FastMCPServer` (application/mcp_server.py:84)
  - All PR URLs validated before processing
  - Parameters sanitized to prevent injection attacks
  - Security exceptions caught and logged safely
  - Failed security validations tracked in metrics

## Code Search with mgrep

This project uses **mgrep** for semantic code search. mgrep provides natural-language search capabilities that understand intent, not just exact patterns.

**Search Examples:**

```bash
mgrep "where do we set up auth?" src/lib
mgrep "how are guarantees created?"
mgrep -m 25 "store schema"  # limit results to 25
mgrep -a "What code parsers are available?"  # generate an answer based on results
```

**Key Options:**

| Option | Description |
|--------|-------------|
| `-m <count>` | Maximum number of results (default: 10) |
| `-c`, `--content` | Show content of results |
| `-a`, `--answer` | Generate AI answer based on results |
| `-s`, `--sync` | Sync files before searching |
| `--no-rerank` | Disable result reranking |
