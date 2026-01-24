# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Current Version:** 0.4.8

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

PRDiffer Overview

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
uv run python prdiffer/server.py

# Run with different transport/port via environment variables
TRANSPORT=sse PORT=9102 uv run python prdiffer/server.py
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

### Domain Layer (`prdiffer/domain/`)

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

### Infrastructure Layer (`prdiffer/infrastructure/`)

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

### Application Layer (`prdiffer/application/`)

- **MCP Server** (`mcp_server.py`):
  - FastMCP server exposing `get_pr_diff` tool
  - Tool registration and request handling
  - Dependency injection orchestration
  - 13 injected dependencies for comprehensive PR diff retrieval
- **Components** (`components/`):
  - `AuthenticationMiddleware` (602 lines): API key authentication with SHA-256 hashing
    - SHA-256 hashed API keys (never stored in plaintext)
    - Admin API key support with elevated privileges
    - Brute-force protection with exponential backoff
    - Client lockout mechanism (5 failures per minute = 60s lockout)
    - JWT token parsing and expiration checking
    - Runtime API key management (add/remove)
    - Multiple authentication headers support (X-API-Key, Authorization Bearer)
    - Thread-safe with `threading.RLock()`
  - `RateLimiter` (214 lines): Per-client rate limiting
    - Token bucket algorithm: 100 requests per minute per client
    - Automatic cleanup of inactive clients (1 hour TTL)
    - Global rate monitoring across all clients
    - Thread-safe with `threading.Lock()`
  - `MetricsTracker` (220 lines): Request metrics tracking
    - Request counting (total, successful, failed)
    - Operation-specific metrics (execution time, success rate)
    - Uptime tracking with human-readable format
    - Request ID generation (REQ-{timestamp}-{counter})
  - `HealthMonitor` (114 lines): Server health checks
    - Aggregates metrics from metrics tracker and rate limiter
    - Health status: healthy/degraded/unhealthy
    - Status thresholds: success rate < 80% OR remaining rate limit < 10% = degraded
  - `ServerConfiguration` (157 lines): Runtime configuration
    - Logging configuration from settings
    - Transport validation (stdio, http, sse, streamable-http)
    - Port validation (1-65535 for non-stdio transports)
    - Configuration validation with warnings/errors
  - `PROperationHandler` (264 lines): PR operations coordination
    - PR diff fetching via GitHub API
    - Repository caching for efficiency
    - URL parsing with regex: `r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"`
    - Lazy repository initialization
- **Factory** (`factory.py`):
  - `create_mcp_server`: Component wiring and injection
  - Two factory functions: primary (with interfaces) and legacy (backward compatibility)
- **Interfaces** (`interfaces/protocols.py` - 230 lines):
  - `RateLimiterProtocol`: check_rate_limit(), increment_rate_limit(), get_rate_limit_info()
  - `MetricsTrackerProtocol`: track_request(), get_metrics_summary(), generate_request_id()
  - `PROperationHandlerProtocol`: get_pr_diff(), describe_pr(), approve_pr(), review_pr(), update_pr_changelog()
  - `HealthMonitorProtocol`: check_health()
  - `ServerConfigurationProtocol`: setup_logging(), get_server_info(), get_mcp_instructions()
  - `AuthenticationProtocol`: authenticate(), extract_client_identifier(), is_authentication_enabled(), get_status()

### Interface Layer

- **Server Entry Point**: `prdiffer/server.py` - main server launcher with dependency initialization

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

### Security Configuration

**IMPORTANT**: Authentication is **enabled by default** for production security. When deploying or developing:

```toml
# In settings.toml
[auth]
enabled = true  # Default: ENABLED for security
```

**To disable authentication for local development**:
```bash
# Set environment variable before starting server
export MCP_AUTH_ENABLED=false
uv run python prdiffer/server.py
```

**To configure API keys**:
```bash
# Set one or more API keys
export MCP_API_KEYS="your-api-key-1,your-api-key-2"

# Set admin API key for elevated privileges
export MCP_ADMIN_API_KEY="your-admin-api-key"
```

**Authentication Features**:
- API key-based authentication with SHA-256 hashing
- Per-client rate limiting to prevent abuse
- Brute-force protection with lockout mechanism
- Multiple API key support for different clients
- Admin API key for elevated privileges

**Environment Variable Reference**:
| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_AUTH_ENABLED` | Enable/disable authentication | `true` |
| `MCP_API_KEYS` | Comma-separated API keys | - |
| `MCP_ADMIN_API_KEY` | Admin API key | - |
| `MCP_MAX_FAILURES_PER_MINUTE` | Max auth failures before lockout | `5` |
| `MCP_LOCKOUT_DURATION` | Lockout duration in seconds | `60` |

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

#### Structured Error Codes

The domain layer defines standardized error codes (`prdiffer/domain/errors.py`):

**Error Categories**:
- **E1xxx**: Input validation errors (E1001-E1006)
- **E2xxx**: Authentication/authorization errors (E2001-E2003)
- **E3xxx**: Rate limiting errors (E3001-E3003)
- **E4xxx**: Resource not found errors (E4001-E4004)
- **E5xxx**: Internal server errors (E5001-E5005)

**Error Code Structure**:
```python
@dataclass(frozen=True)
class ErrorCode:
    code: str           # e.g., "E1001_INVALID_URL"
    name: str           # e.g., "Invalid URL"
    message: str        # User-friendly error message
    remediation: str    # How to fix the error
    category: ErrorCategory
```

#### Exception Hierarchy

The domain layer provides a comprehensive exception hierarchy (`prdiffer/domain/exceptions.py`):

**Base Exception**: `PRDifferException` with message and details

**Exception Categories** (27 total):
- **Authentication**: AuthenticationError, InvalidTokenError, ExpiredTokenError, MissingTokenError, AuthorizationError, InsufficientPermissionsError
- **Rate Limiting**: RateLimitError, GlobalRateLimitError, UserRateLimitError
- **Validation**: ValidationError, InvalidURLError, InvalidRepositoryError, InvalidPRNumberError, UnsupportedFormatError
- **GitHub API**: GitHubAPIError, RepositoryNotFoundError, PRNotFoundError, FileNotFoundError, GitHubAuthenticationError, GitHubConnectionError, GitHubRateLimitError
- **Cache**: CacheError, CacheInvalidationError, CacheCorruptionError
- **Configuration**: ConfigurationError, MissingConfigurationError, InvalidConfigurationError, SecretsError
- **Processing**: ProcessingError, DiffGenerationError, FileProcessingError, PatternMatchingError
- **Resource**: ResourceError, ResourceExhaustedError, MemoryLimitError, TimeoutError
- **Security**: SecurityError, SuspiciousOperationError, InputSanitizationError, SignatureVerificationError

**Helper Functions**:
- `get_exception_details(exception)`: Extracts exception metadata
- `wrap_github_exception(exception)`: Wraps PyGithub exceptions

### Domain Configuration

#### GitHubConfig

The `GitHubConfig` dataclass (`prdiffer/domain/config/github_config.py`) provides frozen configuration for GitHub operations:

**Configuration Groups**:
- **Basic API Settings**: rate_limit, timeout, max_retries, retry_delay
- **Smart Retry**: retry_on_404 (false), retry_on_403 (true), retry_on_500 (true), retry_log_level, permanent_failure_log_level
- **Circuit Breaker & Adaptive Retry**: circuit_breaker_enabled, circuit_breaker_failure_threshold, circuit_breaker_timeout, adaptive_retry_enabled, max_adaptive_delay, api_health_tracking, context_aware_retry
- **File Filtering**: ignore_patterns (tuple), valid_extensions (tuple) - 60+ file types supported
- **Parallel Diff Processing**: diff_parallel_enabled, diff_parallel_threshold (3), diff_max_workers (4), diff_worker_timeout (30.0)
- **File Processing Limits**: max_files_allowed (50), large_file_threshold, chunk_size, max_diff_size

**Methods**:
- `from_dict(config)`: Factory method for dict-to-instance conversion
- `to_dict()`: Instance-to-dict conversion
- `with_overrides(**kwargs)`: Config cloning with overrides
- `should_use_circuit_breaker`, `should_use_adaptive_retry`, `should_track_api_health`, `should_use_parallel_diff`: Derived boolean properties
- `should_ignore_file(filename)`: Uses fnmatch for pattern matching
- `has_valid_extension(filename)`: Extension validation
- `should_process_file(filename)`: Combined validation (ignore patterns + valid extensions)

#### Constants

Centralized constants (`prdiffer/domain/constants.py`):

**Classes**:
- **Limits**: URL/input validation, GitHub API, cache, request coalescing, file processing, circuit breaker, parallel processing limits
- **Thresholds**: File change thresholds (SIGNIFICANT_CHANGES, LARGE_CHANGES), retry thresholds, lockout duration
- **Defaults**: MCP server, authentication, cache, logging, token validation defaults
- **Timeouts**: API and request timeouts
- **RegularExpressions**: GitHub URL patterns, command injection, path traversal, SQL injection, Git ref validation patterns

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

## Test Structure

The codebase has a comprehensive test suite with **50+ test files** organized across unit, integration, and performance layers:

### Test Organization

```
tests/
├── unit/                                    # Unit Tests
│   ├── application/                         # Application Layer Tests
│   │   ├── components/                      # Component tests
│   │   │   ├── test_authentication.py
│   │   │   ├── test_health_monitor.py
│   │   │   ├── test_metrics_tracker.py
│   │   │   └── test_rate_limiter.py
│   ├── domain/                              # Domain Layer Tests
│   │   ├── entities/                        # Entity tests
│   │   ├── services/                        # Service interface tests
│   │   ├── usecases/                        # Use case tests
│   └── infrastructure/                      # Infrastructure Layer Tests
│       ├── github/                          # GitHub component tests
│       ├── utils/                           # Utility tests
│       └── [infrastructure component tests]
├── integration/                             # Integration Tests
│   ├── test_complete_workflow.py
│   ├── test_error_scenarios.py
│   ├── test_security.py
│   └── test_real_github_api.py
└── performance/                             # Performance Tests
    └── test_performance.py
```

### Test Markers

- `@pytest.mark.unit` - Unit tests (isolated, fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may use external services)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.security` - Security and vulnerability tests
- `@pytest.mark.thread_safety` - Thread safety and concurrency tests

### Key Test Features

**Comprehensive Security Testing**:
- 571 lines of validation tests in `test_input_validator.py`
- SQL injection, command injection, path traversal prevention tests
- Rate limiting and brute-force protection tests

**Phase-Based Organization**:
- Phase 1: Critical fixes (LRU cache, TTL, retry handler, circuit breaker)
- Phase 2: Diff builder optimization (binary files, chunked processing, streaming)
- Phase 3: API enhancement (extended FilePatchInfo, PRDiff, error codes)
- Phase 4: Architecture refinement (GitHubConfig, AsyncParallelExecutor, circuit breakers)

**Thread Safety Testing**:
- Concurrent cache operations (100 threads)
- Circuit breaker concurrent failures/successes
- Request coalescing thread safety

**Async Testing**:
- Full pytest-asyncio support
- Anyio task group testing
- Timeout handling tests

### Coverage Goals

| Layer | Target Coverage |
|-------|----------------|
| Overall | >80% |
| Domain | >90% (critical business logic) |
| Infrastructure | >75% (external dependencies) |
| Application | >85% (application orchestration) |

## OpenSpec System

PRDifferMCP uses **OpenSpec** for spec-driven development workflow:

### OpenSpec Directory Structure

```
openspec/
├── AGENTS.md                   # Instructions for AI coding assistants (456 lines)
├── project.md                  # Project conventions and metadata (230 lines)
├── specs/                      # Current truth - what IS built
│   └── [capability]/
│       ├── spec.md             # Requirements and scenarios
│       └── design.md           # Technical patterns (optional)
├── changes/                    # Proposals - what SHOULD change
│   ├── [change-id]/
│   │   ├── proposal.md        # Why, what, impact
│   │   ├── tasks.md           # Implementation checklist
│   │   ├── design.md          # Technical decisions (optional)
│   │   └── specs/             # Delta changes
│   └── archive/              # Completed changes (YYYY-MM-DD-[name]/)
```

### OpenSpec Workflow (Three-Stage)

**Stage 1: Creating Changes**
- Create proposal for new features, breaking changes, architecture shifts
- Skip for bug fixes, typos, non-breaking updates
- Choose unique kebab-case `change-id` (verb-led)

**Stage 2: Implementing Changes**
1. Read proposal.md
2. Read design.md (if exists)
3. Read tasks.md
4. Implement tasks sequentially
5. Update checklist when complete

**Stage 3: Archiving Changes**
1. Move `changes/[name]/` → `changes/archive/YYYY-MM-DD-[name]/`
2. Update specs/ if capabilities changed
3. Run `openspec validate --strict`

### Key Commands

```bash
openspec list                  # List active changes
openspec list --specs          # List specifications
openspec show [item]           # Display change or spec
openspec validate [item]       # Validate changes or specs
openspec archive <change-id>   # Archive after deployment
```

### Spec File Format Requirements

**Critical**: Scenario formatting must use `#### Scenario:` (4 hashes)
```markdown
#### Scenario: User login success
- **WHEN** valid credentials provided
- **THEN** return JWT token
```

**Delta Operations**:
- `## ADDED Requirements` - New capabilities
- `## MODIFIED Requirements` - Changed behavior (must include full requirement)
- `## REMOVED Requirements` - Deprecated features
- `## RENAMED Requirements` - Only name changes

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
