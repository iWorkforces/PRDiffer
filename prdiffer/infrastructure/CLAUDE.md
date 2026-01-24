# CLAUDE.md - Infrastructure Layer

This file provides guidance for working with the Infrastructure Layer of PRDiffer.

**Current Version:** 0.4.8

## Infrastructure Layer Overview

The infrastructure layer contains external integrations, data access implementations, and cross-cutting concerns like settings and logging. This layer implements interfaces defined in the domain layer.

## Key Components

### GitHub Integration (`github_repository.py`)

**GitHubPRDiffRepository**
- Implements `PRDiffRepository` interface from domain layer
- Uses PyGithub library for GitHub API integration
- Handles authentication, rate limiting, and API error handling

**Public Properties:**
- `repo_owner` (str): Repository owner/organization name (read-only)
- `repo_name` (str): Repository name (read-only)
- `pr_number` (int): Pull request number (read-only)

**Public Methods:**
- `async get_latest_commit_sha() -> str`: Gets the latest head commit SHA for cache validation
- `async get_pr_diff() -> PRDiff`: Fetches complete PR diff with full context

**Factory Function:**
```python
def get_github_repository(
    repo_owner: str, repo_name: str, pr_number: int,
    github_token: Optional[str] = None
) -> GitHubPRDiffRepository:
    """Get a GitHub repository instance (singleton pattern per repository/PR).

    This function provides a singleton pattern for GitHubPRDiffRepository instances
    to avoid creating multiple instances for the same repository and PR.

    The cache key format is: `{repo_owner}/{repo_name}/pr/{pr_number}` with optional
    `/token` suffix when github_token is provided.

    Returns:
        GitHubPRDiffRepository: The repository instance
"""
```

**Critical Implementation Details:**

**Caching Architecture:**
- Settings service uses manual caching instead of `@lru_cache` 
- Reason: Dynaconf objects are not hashable, causing `TypeError: unhashable type: 'list'`
- Solution: Manual cache variables with list-to-tuple conversion for hashability

**Full-File Diff Generation:**
- `_build_full_file_patch()`: Creates complete file context diffs (not minimal hunks)
- Method signature: Instance method (not static) for proper `self._build_full_file_patch()` calls
- Uses `difflib.SequenceMatcher` for accurate line-by-line comparison
- Output format: `@@ -1,134 +1,139 @@` style headers with full file context

**File Content Processing Pipeline:**
1. **File Retrieval**: `_get_files()` via PyGithub API
2. **File Filtering**: `_filter_files()` based on `ignore_patterns`/`valid_extensions` settings
3. **Content Loading**: `_get_pr_file_content()` for base/head commits (limited by `max_files_allowed`)
4. **Patch Generation**: `_extend_patch()` creates full-file unified diffs
5. **Extended Diff**: `_pr_generate_extended_diff()` formats with headers and context

**GitHub API Strategies:**
- **Authentication**: parameters → `GITHUB_TOKEN` env variable (settings no longer used for tokens)
- **Merge Base Handling**: Uses `repo.compare()` to find proper base commit (handles parallel merges)
- **Rate Limiting**: Configurable limits with graceful degradation
- **Content Encoding**: Multiple encoding attempts (UTF-8, iso-8859-1, latin-1, ascii, utf-16)

**Merge Base Commit Logic:**
The `_get_merge_base_commits()` method (line 383) ensures accurate diff comparison by:

1. **Using GitHub's Compare API**: `repo.compare(base_sha, head_sha)` to get merge base
2. **Parallel Merge Handling**: Correctly handles cases where multiple commits merge into the same target
3. **Fallback Strategy**: Falls back to base commit SHA if merge base detection fails
4. **Logging**: Logs when using merge base instead of direct base for transparency

**Merge base is important** because:
- Direct base commits may not reflect the common ancestor for diff generation
- Parallel merges require finding the true merge base for accurate diffs
- GitHub's compare API provides the correct merge base commit SHA

**Safe Logging Patterns:**
- `_sanitize_filename_for_logging()` (line 432): Sanitizes filenames to prevent log injection
- `_log_filtered_files()` (line 445): Logs filtered file information with sanitized names
- All user inputs sanitized before logging to prevent log injection attacks

### Settings Management (`settings.py`)

**SettingsService**
- Uses Dynaconf for TOML configuration with environment overrides
- Implements manual caching to avoid `@lru_cache` hashability issues
- Converts lists to tuples for hashable cache keys

**Key Methods:**
- `get()`: Manual caching with hashable key conversion
- `get_github_settings()`: Returns tuple-converted lists for `ignore_patterns`/`valid_extensions`
- `clear_cache()`: Manual cache clearing

**Configuration Structure:**
- Uses `[default]` section (supports optional environment overrides like `[development]`, `[production]`, `[testing]` if needed)
- GitHub, MCP, cache, and application settings sections
- File filtering patterns and extensions

### GitHub API Configuration

The GitHub API integration provides comprehensive configuration options for managing API interactions, retry behavior, circuit breaking, and performance optimization.

**Basic API Settings** (in `settings.toml`):
```toml
# GitHub API settings
github.rate_limit = 5000          # API rate limit (requests per hour)
github.timeout = 30               # Request timeout in seconds
github.max_retries = 3            # Maximum retry attempts for failed requests
github.retry_delay = 1            # Base delay between retries (seconds)
```

**Smart Retry Settings** (Phase 2):
```toml
# Smart retry settings
github.retry_on_404 = false       # Don't retry 404 errors (file not found - permanent)
github.retry_on_403 = true        # Retry 403 errors (might be rate limiting)
github.retry_on_500 = true        # Retry 5xx server errors (transient)
github.retry_log_level = "DEBUG"  # Log retry attempts at DEBUG level
github.permanent_failure_log_level = "INFO"  # Log permanent failures at INFO level
```

**Circuit Breaker Configuration** (Phase 3):
```toml
# Circuit breaker pattern - prevents cascading failures
github.circuit_breaker_enabled = true           # Enable circuit breaker pattern
github.circuit_breaker_failure_threshold = 5    # Failures before opening circuit
github.circuit_breaker_timeout = 60             # Seconds to keep circuit open
```

The circuit breaker pattern provides:
- **Closed State**: Normal operation, requests flow through
- **Open State**: Circuit is open after threshold failures, requests fail fast
- **Half-Open State**: Test if service has recovered after timeout

**Adaptive Retry Configuration** (Phase 3):
```toml
# Adaptive retry with health-aware backoff
github.adaptive_retry_enabled = true    # Enable adaptive retry delays
github.max_adaptive_delay = 30          # Maximum adaptive delay (seconds)
```

Adaptive retry adjusts delays based on:
- API health metrics (response times, error rates)
- Recent failure patterns
- Exponential backoff with jitter
- Maximum delay cap to prevent excessive waits

**API Health Tracking** (Phase 3):
```toml
# API performance monitoring
github.api_health_tracking = true       # Track API health metrics
github.context_aware_retry = true       # Enable context-aware retry strategies
```

Health tracking provides:
- Response time monitoring (p50, p95, p99)
- Error rate tracking by error type
- Health-based backoff adjustment
- Performance degradation detection

**Parallel Diff Processing** (Phase 3):
```toml
# Parallel diff generation for large PRs
github.diff_parallel_enabled = true     # Enable parallel diff generation
github.diff_parallel_threshold = 3      # Minimum files to trigger parallel processing
github.diff_max_workers = 4             # Maximum worker threads for parallel processing
github.diff_worker_timeout = 30.0       # Timeout per file in seconds
```

Parallel processing provides:
- Concurrent file content retrieval
- Faster diff generation for large PRs
- Configurable worker pool size
- Per-file timeout protection

**File Filtering Configuration**:
```toml
# File filtering patterns
github.ignore_patterns = [
    "*.lock", "package-lock.json", "*.log", "*.tmp", "*.bak",
    "node_modules/", "dist/", "build/", ".git/", "__pycache__/"
]

github.valid_extensions = [
    ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
    ".java", ".kt", ".scala", ".cpp", ".c", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".swift", ".md", ".json", ".yml"
]
```

**Configuration Trade-offs:**

| Setting | Performance | Reliability | Memory Usage |
|---------|-------------|--------------|--------------|
| `diff_parallel_enabled=true` | Higher (concurrent) | Same | Higher |
| `circuit_breaker_enabled=true` | Same (fast fail) | Higher | Lower |
| `adaptive_retry_enabled=true` | Variable | Higher | Same |
| `api_health_tracking=true` | Slight overhead | Higher | Low |

### Cache Services

**CacheService (`cache_service.py`)**
- Provides in-memory caching for PR diff data with commit-based invalidation
- Implements MD5-based key hashing to reduce memory usage for long repository names
- Maintains reverse mapping for debugging and statistics
- Singleton pattern via `get_cache_service()`

**Key Features:**
- **Commit-Based Invalidation**: Cache keys include commit SHA to automatically invalidate stale data
- **MD5 Hashing**: Converts variable-length keys to fixed 32-character hashes
- **Reverse Mapping**: Optional hash→original mapping for debugging (configurable)
- **Environment-Aware**: Hashing enabled in production, disabled in development for easier debugging
- **Dual Logging**: Logs both original key and hash for maximum visibility

**Configuration** (in `settings.toml`):
```toml
cache.use_hashed_keys = true           # Enable/disable hashing
cache.hash_algorithm = "md5"            # Hash algorithm (md5, sha256, sha256_short)
cache.store_key_mapping = true          # Store hash→original mapping
```

**Key Methods:**
- `get_cache_key(owner, name, pr_number)`: Generate original cache key (external API)
- `_hash_key(key)`: Internal MD5 hashing function
- `_get_internal_key(original_key)`: Convert to internal key (hashed or original)
- `_get_original_key(internal_key)`: Reverse lookup via mapping
- `get(cache_key, commit_sha)`: Retrieve cached data with commit validation
- `set(cache_key, commit_sha, data)`: Store data with commit SHA
- `invalidate(cache_key)`: Remove from cache and mapping
- `clear()`: Clear all cache and mapping data
- `get_stats()`: Statistics with original keys (if mapping enabled)

**Implementation Details:**
- **External API**: Always uses original keys (`owner/repo/pr/number` format)
- **Internal Storage**: Uses MD5 hash when hashing is enabled
- **Logging Format**: `Cache set [cache_key=owner/repo/pr/123 hash=a7b3c4d5... commit_sha=abc123]`
- **Memory Trade-off**: Hash (32 bytes) + mapping overhead vs. variable-length original keys
- **Hash Consistency**: Same key always produces same hash (MD5 deterministic)

**Benefits of Hashing:**
- **Memory Efficiency**: Fixed-length keys reduce memory for repos with long names
- **Consistent Size**: All keys are exactly 32 characters (MD5)
- **Fast Lookup**: MD5 hashing is very fast (microseconds)
- **Collision Resistant**: MD5 sufficient for cache keys (not cryptographic use)

**Debugging Support:**
- **Original Keys in Stats**: `get_stats()` returns human-readable keys when mapping enabled
- **Dual Logging**: Both original and hash logged for traceability
- **Reverse Mapping**: Can always trace hash back to original key
- **Configurable**: Can disable hashing via `cache.use_hashed_keys = false` if needed for debugging

**RepositoryCacheService (`repository_cache_service.py`)**
- Caches GitHubPRDiffRepository instances to avoid repeated GitHub API initialization
- Uses tuple-based cache keys `(repo_owner, repo_name, pr_number)`
- Tuple keys are already efficient (hashable, compact) - no hashing needed
- Implements TTL-based expiration and LRU eviction

**Note**: RepositoryCacheService does not use key hashing because:
1. Tuple keys are already memory-efficient and hashable
2. No long string keys that would benefit from hashing
3. Logs display individual fields, not combined keys
4. Different use case (caching objects vs. caching data)

### Request Coalescing Service (`request_coalescing.py`)

**RequestCoalescingService**
- Deduplicates concurrent requests for the same resource
- Uses anyio primitives (Lock, Event) for thread-safe operation
- Prevents duplicate GitHub API calls when multiple concurrent requests arrive
- Implements singleton pattern via `get_request_coalescing_service()`

**Key Features:**
- **Atomic State Management**: Uses `anyio.Lock` for thread-safe request tracking
- **Result Sharing**: Uses `anyio.Event` to notify waiting requests when result is available
- **Timeout Protection**: Configurable timeout (default 30s) prevents indefinite waiting
- **Waiter Tracking**: Counts concurrent waiters for each request
- **Statistics**: Provides metrics on pending requests and total waiters
- **Proper Cleanup**: Ensures cleanup on success, failure, and timeout

**Request Flow:**
1. Request arrives with unique key (e.g., "owner/repo/pr/123")
2. Check if request already in progress
   - If yes: Wait for existing request to complete
   - If no: Create new request and execute fetch function
3. Share result with all waiting requests
4. Clean up request tracking

**Usage Pattern:**
```python
coalescing_service = get_request_coalescing_service()
result = await coalescing_service.coalesce(
    key="owner/repo/pr/123",
    fetch_func=lambda: fetch_from_github_api(),
    timeout=30.0
)
```

**Benefits:**
- Reduces GitHub API calls under high concurrency
- Prevents rate limit exhaustion from duplicate requests
- Improves response time for concurrent requests
- Provides observability through statistics

### Async Parallel Executor (`async_parallel_executor.py`)

**AsyncParallelExecutor**
- Native async parallel processing using anyio task groups
- Replaces ThreadPoolExecutor for better async performance
- Multiple error handling strategies
- Implements singleton pattern via `get_async_parallel_executor()`

**Key Features:**
- **Anyio Task Groups**: Uses `anyio.create_task_group()` for structured concurrency
- **Semaphore Control**: Limits concurrent operations with `anyio.Semaphore`
- **Error Strategies**: IGNORE, RAISE, COLLECT, CONTINUE
- **BatchResult**: Tracks successful and failed operations separately
- **Progress Tracking**: Optional progress callbacks for long-running operations
- **Multiple Execution Modes**: batch, context-based, mapped, with progress

**Error Handling Strategies:**
1. **IGNORE** (default): Log errors, return only successful results
2. **RAISE**: Raise first exception encountered
3. **COLLECT**: Return both successful results and errors
4. **CONTINUE**: Continue processing, return detailed batch results

**Execution Modes:**
```python
executor = AsyncParallelExecutor(max_concurrent=10, timeout=30.0)

# Basic batch processing
results = await executor.execute_batch(async_func, items)

# With shared context
results = await executor.execute_batch_with_context(async_func, items, context)

# Mapped execution (different functions for different item types)
results = await executor.execute_mapped_batch(func_map, items, default_func)

# With progress tracking
results = await executor.execute_with_progress(
    async_func, items,
    progress_callback=lambda done, total: print(f"{done}/{total}")
)
```

**Performance Benefits:**
- Better than ThreadPoolExecutor for I/O-bound async operations
- No thread context switching overhead
- Efficient resource usage with semaphore-based control
- Structured concurrency ensures proper cleanup

**Use Cases:**
- Parallel file content fetching from GitHub API
- Batch processing of PR files
- Concurrent diff generation for multiple files
- Any async I/O operations that benefit from parallelization

### Logging System (`logging/`)

**Architecture:**
- **Domain Service**: `LoggerService` abstract interface in domain layer
- **Infrastructure Implementation**: `ConsoleLogger` in infrastructure layer
- **Global Access**: `get_logger()` singleton pattern

**ConsoleLogger Features:**
- ANSI color-coded output (DEBUG=Cyan, INFO=Green, WARNING=Yellow, ERROR=Red, CRITICAL=Magenta)
- Structured logging with context data via `**kwargs`
- Log level filtering based on settings
- Timestamp formatting and stderr routing for errors

### Factory Implementation (`factories/`)

**InfrastructureFactory** (`infrastructure_factory.py`)
Concrete implementation of `InfrastructureFactoryInterface` from the domain layer.

**Purpose:**
- Creates all infrastructure service instances
- Implements dependency injection patterns
- Provides singleton access for shared services
- Wires dependencies for complex services

**Key Factory Methods:**
- `create_settings_service()` - Uses `get_settings_service()` singleton
- `create_logger_service()` - Uses `get_logger()` singleton
- `create_cache_service()` - Uses `get_cache_service()` singleton
- `create_pr_diff_service()` - Creates `GitHubPRDiffService` with all dependencies

**Factory Function:**
```python
def get_infrastructure_factory() -> InfrastructureFactoryInterface:
    return InfrastructureFactory()
```

See `factories/CLAUDE.md` for detailed documentation.

### Service Implementations (`services/`)

**GitHubPRDiffService** (`pr_diff_service.py`)
Concrete implementation of `PRDiffServiceInterface` from the domain layer.

**Purpose:**
- Provides PR diff operations using GitHub API
- Orchestrates diff generation workflow
- Handles error cases with graceful degradation

**Key Methods:**
- `get_pr_diff(repo_owner, repo_name, pr_number)` - Fetches complete PR diff data
- `get_latest_commit_sha(...)` - Gets latest commit SHA for caching
- `validate_repository_access(...)` - Validates repository accessibility

**Dependencies:**
- `GitHubAPIClient` - API operations
- `DiffGenerator` - Diff content generation
- `FileProcessor` - File filtering and validation
- `LoggerService` - Structured logging

See `services/CLAUDE.md` for detailed documentation.

### Utility Components (`utils/`)

Additional utility components discovered in the infrastructure layer:

**GlobalCircuitBreakerRegistry** (`circuit_breaker.py`)
- Global registry for circuit breakers across the application
- Per-endpoint circuit breakers for targeted protection
- Global circuit breaker for system-wide protection
- Statistics aggregation across all breakers
- Methods: `get_breaker(endpoint)`, `can_execute(endpoint)`, `record_success/failure(endpoint)`, `get_all_stats()`, `get_open_breakers()`

**apply_diff_limits** (`diff_limits.py`)
- Enforces diff size limits and returns truncation metadata
- `apply_diff_limits(diff_content, max_chars, truncation_notice)` - Applies character limits to diff content
- Prevents memory exhaustion from large diffs

**ExceptionSanitizer** (additional methods in `exception_utils.py`)
- `sanitize_exception_message(message)` - Sanitizes exception message
- `sanitize_traceback(traceback, frame_limit=None)` - Sanitizes traceback with frame limit
- `sanitize_exception_for_logging(exception)` - Creates safe logging representation
- `redact_auth_header(header_value)` - Redacts authorization header values
- Redaction patterns: GitHub tokens, generic tokens, passwords, emails (u***@d***.com), IPs (192.168.*.*), API keys in URLs/headers

## Thread Safety Guarantees

The infrastructure layer implements comprehensive thread safety mechanisms to ensure correct behavior under concurrent access:

### CacheService Thread Safety

- **Reentrant Lock Protection**: All cache operations protected by `threading.RLock()`
- **Atomic Operations**: Statistics counters (`_cache_hits`, `_cache_misses`) updated atomically
- **Double-Check Locking**: Fast path without lock in `_get_internal_key()`, slow path with lock
- **Thread-Safe Statistics**: `get_stats()` returns consistent snapshots under lock

### RequestCoalescingService Thread Safety

- **Memory Safety**: Maximum waiter limit (default: 100) prevents resource exhaustion
- **Atomic State Management**: `anyio.Lock` ensures atomic request tracking
- **Proper Cleanup**: `_decrement_waiter()` ensures cleanup on all exit paths
- **Timeout Protection**: `anyio.fail_after()` prevents indefinite waits

### FileProcessor Thread Safety

- **Double-Check Locking**: Fast path cache check, slow path with lock for initialization
- **Cache Lock**: `_cache_lock` (reentrant) protects PR files cache
- **Thread-Safe Updates**: Cache initialization and updates protected by lock

### CacheDecorator Thread Safety

- **CachingMixin**: Thread-safe with `threading.RLock()` protection
- **Protected Operations**: All cache modifications (get, set, clear) under lock
- **Safe Cleanup**: `clear_method_cache()` properly locked

### Thread Safety Patterns Used

- **Reentrant Locks (`RLock`)**: For recursive access patterns
- **Double-Check Locking**: Fast path without lock, slow path with lock
- **Anyio Primitives**: `Lock`, `Semaphore`, `Event` for async concurrency
- **Atomic State Management**: All state transitions protected by locks
- **Proper Cleanup**: try-finally blocks ensure cleanup on all exit paths

### Exception Handling (Production Safety)

- **Assertions Replaced**: All `assert` statements replaced with `RuntimeError` exceptions
- **GitHubPRDiffRepository**: 7 assertions → proper exceptions
- **RequestCoalescingService**: 1 assertion → proper exception
- **PROperationHandler**: Logic bug fixed + assertion removed

## Security Features

The infrastructure layer implements comprehensive security measures to protect against common vulnerabilities:

### Exception Sanitization (`exception_utils.py`)

- **ExceptionSanitizer Class**: Redacts sensitive data from exception messages
- **Token Redaction Patterns**: GitHub tokens, generic tokens, passwords
- **PII Protection**: Email addresses and IP addresses partially redacted
- **Usage Throughout**: Applied in 15+ locations across codebase

**Redaction Patterns:**

- GitHub tokens: `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_` prefixes
- Generic tokens: `token`, `apikey`, `api_key`, `access_token`
- Passwords: `password`, `passwd`, `pwd` keywords
- Emails: `user@domain.com` → `u***@d***.com`
- IPs: `192.168.1.1` → `192.168.*.*`

### Input Validation (`security/input_validator.py`)

- **URL Validation**: GitHub PR URL validation with strict patterns
- **Branch/Ref Validation**: Git ref naming rules enforcement (`validate_branch_name()`)
- **Repository Validation**: Owner and repo name validation against GitHub conventions
- **PR Number Validation**: Positive integer within valid range
- **String Sanitization**: Removes control characters, checks for null bytes
- **Suspicious Pattern Detection**: Command injection, path traversal, SQL injection

**Validation Methods:**

- `validate_github_url()`: Comprehensive URL validation with security checks
- `validate_repository_identifier()`: Repository owner/name validation
- `validate_pr_number()`: PR number validation
- `validate_branch_name()`: Git ref naming rules
- `validate_token_format()`: Token format validation
- `validate_user_id()`: User identifier validation
- `sanitize_for_logging()`: Prevents log injection attacks

### Safe Logging Practices

- **Sanitization Before Logging**: All user inputs sanitized before logging
- **Control Character Removal**: Prevents log injection through ANSI codes
- **Length Limits**: Prevents log flooding through overly long messages
- **Structured Logging**: Context data passed as kwargs (not string interpolated)

**Example:**

```python
# Safe logging with sanitization
safe_url = self._input_validator.sanitize_for_logging(user_url)
self._logger.info("Processing PR", url=safe_url)
```

### Security Configuration

- **Settings Integration**: Security settings in `settings.toml`
- **Environment-Specific**: Different settings for development/production
- **Security Headers Documentation**: nginx examples for CSP, X-Frame-Options, etc.

## Development Guidelines

### Working with GitHub API
- Always handle `Exception` gracefully (return empty strings rather than failing)
- Use merge base commits for accurate diff comparison
- Implement file content loading limits to avoid rate limiting
- Test with both authenticated and anonymous access

### Settings Management
- Never use `@lru_cache` on methods with `self` parameter containing Dynaconf
- Convert lists to tuples when storing in cache keys
- Use environment-specific settings for different deployment contexts
- Clear cache when settings change

### Logging Best Practices
- Use structured logging with context: `logger.info("message", key=value)`
- Check log levels in performance-critical paths
- Route errors/critical to stderr, info/debug to stdout
- Include relevant request context in log messages

### File Processing Optimization
- Implement file filtering early to reduce API calls
- Use full-file context for better diff analysis
- Handle binary files and encoding errors gracefully
- Respect GitHub API rate limits with proper error handling

## Critical Technical Issues Resolved

### Serialization Problem (`TypeError: unhashable type: 'list'`)
**Root Cause:** `@lru_cache` tried to hash `SettingsService` instance containing unhashable Dynaconf objects
**Solution:** Replaced with manual caching using instance variables

### Method Signature Bug (`_build_full_file_patch`)
**Root Cause:** Method defined as static but called as instance method
**Solution:** Changed to instance method: `def _build_full_file_patch(self, ...):`

### Output Formatting Issue
**Root Cause:** Missing blank line after file headers in diff output
**Solution:** Added extra `\n` in format string: `f"\n\n## File: '{filename}'\n\n{patch}"`

## External Dependencies

- **PyGithub**: GitHub API client library for GitHub integration
- **Dynaconf**: Configuration management with TOML support and environment overrides
- **anyio**: Async compatibility layer providing backend-agnostic async operations
- **asyncer**: Additional async utilities and helpers
- **python-dotenv**: Environment variable loading from .env files
- **FastMCP**: MCP (Model Context Protocol) framework for server implementation
- **Standard Library**: `difflib`, `re`, `logging`, `datetime`, `asyncio`

## Key Technologies

### Async Framework Migration
The infrastructure layer has been migrated from raw `asyncio` to `anyio` for:
- **Better Portability**: Works with multiple async backends (asyncio, trio, etc.)
- **Cleaner APIs**: More intuitive async primitives and structured concurrency
- **Testing Support**: Better integration with pytest-asyncio
- **Future Compatibility**: Easier migration to alternative async frameworks if needed

### Anyio Primitives in Use
- **anyio.Semaphore**: Concurrent operation control in AsyncParallelExecutor
- **anyio.Lock**: Mutual exclusion in RequestCoalescingService
- **anyio.Event**: Async event signaling for request result notification
- **anyio.create_task_group()**: Parallel task execution with structured concurrency
- **anyio.fail_after()**: Timeout protection for async operations

This infrastructure layer provides robust external integrations while maintaining clean separation from domain logic through well-defined interfaces.

## Performance Benchmarks

### Baseline Metrics

The following baseline metrics were measured using the standard configuration (GitHub API, authenticated requests, 100Mbps network):

| Metric | Value | Conditions | Measurement Method |
|--------|-------|------------|-------------------|
| **API Call Latency (p50)** | 180ms | Single file fetch | Time from request to response |
| **API Call Latency (p95)** | 450ms | Single file fetch | 95th percentile of requests |
| **API Call Latency (p99)** | 850ms | Single file fetch | 99th percentile of requests |
| **Small PR (<10 files)** | 2-5s | Full PR diff processing | End-to-end processing time |
| **Medium PR (10-50 files)** | 8-20s | Full PR diff processing | End-to-end processing time |
| **Large PR (50-100 files)** | 30-60s | Full PR diff processing | End-to-end processing time |
| **Cache Hit Rate** | 85-95% | Repeated PR requests | Cache hits vs total requests |
| **Memory Usage** | 50-150MB | Typical PR processing | Peak memory during processing |
| **Memory Usage** | 200-500MB | Large PR (100+ files) | Peak memory during processing |

### Optimization Results

**String Concatenation Optimization** (v0.4.8):
- **Before**: O(n²) complexity with `+=` operator
- **After**: O(n) complexity with list join
- **Improvement**: 40-60% faster for large diffs (>1000 lines)
- **Measured**: Large diff (5000 lines) reduced from 850ms to 340ms

**Parallel Processing Gains**:
- **Sequential**: 30s for 50-file PR
- **Parallel (4 workers)**: 12s for 50-file PR
- **Improvement**: 2.5x faster for I/O-bound operations
- **Threshold**: Parallel processing enabled when `diff_parallel_threshold >= 3`

**Caching Effectiveness**:
- **Cache Hit**: 50-100ms response time (memory read)
- **Cache Miss**: 2-60s response time (GitHub API fetch)
- **Improvement**: 50-600x faster on cache hit
- **Commit Validation**: Automatic invalidation when PR updated

**Request Coalescing Benefits**:
- **Without Coalescing**: 10 concurrent requests = 10 API calls
- **With Coalescing**: 10 concurrent requests = 1 API call
- **Improvement**: 10x reduction in API calls under high concurrency
- **Rate Limit Protection**: Prevents exhaustion from duplicate requests

### Configuration Tuning Recommendations

Based on benchmarking data, optimal configuration varies by use case:

**For Small PRs (<10 files)**:
```toml
github.diff_parallel_enabled = false     # Sequential is faster
github.max_retries = 2                   # Reduce retries
cache.ttl = 300                          # Shorter cache TTL
```

**For Medium PRs (10-50 files)**:
```toml
github.diff_parallel_enabled = true
github.diff_parallel_threshold = 3       # Default threshold
github.diff_max_workers = 4              # Default workers
cache.ttl = 600                          # Default cache TTL
```

**For Large PRs (50+ files)**:
```toml
github.diff_parallel_enabled = true
github.diff_parallel_threshold = 1       # Always parallel
github.diff_max_workers = 8              # More workers
github.diff_worker_timeout = 60.0        # Longer timeout
app.max_files_allowed = 100              # Allow more files
```

**For High Concurrency**:
```toml
async_parallel_executor.max_concurrent = 20   # Increase parallelism
request_coalescing.max_waiters = 200          # Allow more waiters
github.circuit_breaker_enabled = true         # Prevent cascading failures
github.adaptive_retry_enabled = true          # Adjust to load
```

### Performance Trade-offs

| Configuration | Performance | Reliability | Memory Usage | Recommended For |
|---------------|-------------|--------------|--------------|-----------------|
| `diff_parallel_enabled=true` | Higher | Same | Higher | PRs with 10+ files |
| `circuit_breaker_enabled=true` | Same | Higher | Lower | Production deployments |
| `adaptive_retry_enabled=true` | Variable | Higher | Same | Unreliable networks |
| `api_health_tracking=true` | Slight overhead | Higher | Low | Production monitoring |
| `diff_max_workers=8` | Higher | Same | Higher | Large PRs only |
| `max_files_allowed=100` | Same | Same | Higher | Large PR analysis |

### Performance Monitoring

To collect performance metrics in production:

```python
# Enable API health tracking
github.api_health_tracking = true

# Monitor cache performance
cache_stats = cache_service.get_stats()
print(f"Hit rate: {cache_stats['hit_rate']:.2%}")
print(f"Cache size: {cache_stats['size']}")

# Monitor API health
health_tracker = api_health_tracker
print(f"Error rate: {health_tracker.get_error_rate():.2%}")
print(f"Avg latency: {health_tracker.get_avg_latency():.0f}ms")
```

### Performance Testing

To reproduce benchmarks:

```bash
# Run performance tests
pytest tests/unit/test_performance.py -v

# Profile specific operations
python -m cProfile -o profile.stats prdiffer/server.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
```

## Anyio Backend Selection

The infrastructure layer uses `anyio` as an async compatibility layer, enabling the use of multiple async backends. This provides flexibility in choosing the async runtime that best suits your deployment environment.

### Available Backends

#### asyncio (Default)

**Description**: Python's built-in async/await runtime library

**When to Use**:
- **Default Choice**: Best for most deployments
- **Compatibility**: Works with all Python async libraries
- **Debugging**: Excellent tooling and debugging support
- **Ecosystem**: Largest ecosystem of async libraries

**Pros**:
- Built into Python standard library (3.7+)
- Excellent debugging support with `python -m asyncio`
- Compatible with FastAPI, aiohttp, and other popular frameworks
- Mature and well-documented

**Cons**:
- Can have higher memory overhead than trio
- Task cancellation semantics can be complex

**Configuration**:
```bash
# asyncio is the default backend - no configuration needed
python prdiffer/server.py
```

#### trio

**Description**: A Python library for structured concurrency

**When to Use**:
- **Structured Concurrency**: When you need cleaner async semantics
- **Testing**: For more predictable async test behavior
- **Cancellation**: When you need robust cancellation handling

**Pros**:
- Cleaner concurrency model with nurseries (task groups)
- More predictable cancellation semantics
- Better error messages for concurrency issues
- Lower memory overhead in some scenarios

**Cons**:
- Smaller ecosystem than asyncio
- Not compatible with all async libraries
- Requires additional dependency installation

**Configuration**:
```bash
# Install trio backend
uv pip install trio

# Use trio backend
ANYIO_BACKEND=trio python prdiffer/server.py
```

#### curio

**Description**: A Python library for performing concurrent I/O

**When to Use**:
- **Experimental**: For experimentation with alternative async models
- **Low-Level Control**: When you need fine-grained control over I/O operations

**Pros**:
- Lightweight and efficient
- Simple, clean API
- Good for low-level network programming

**Cons**:
- Smallest ecosystem of the three backends
- Less mature than asyncio and trio
- Not compatible with most async libraries

**Configuration**:
```bash
# Install curio backend
uv pip install curio

# Use curio backend
ANYIO_BACKEND=curio python prdiffer/server.py
```

### Selection Criteria

#### Platform Compatibility

| Backend | Windows | Linux | macOS | Python 3.14 | Notes |
|---------|---------|-------|-------|-------------|-------|
| asyncio | ✅ | ✅ | ✅ | ✅ | Built-in, best compatibility |
| trio | ✅ | ✅ | ✅ | ✅ | Full support |
| curio | ✅ | ✅ | ✅ | ⚠️ | May have issues with latest Python |

#### Feature Requirements

| Feature | asyncio | trio | curio | Recommendation |
|---------|---------|------|-------|----------------|
| HTTP/WebSocket Libraries | ✅ | ⚠️ | ⚠️ | Use asyncio for web services |
| Task Cancellation | ⚠️ | ✅ | ✅ | Use trio for complex cancellation |
| Structured Concurrency | ⚠️ | ✅ | ✅ | Use trio for clean async patterns |
| Ecosystem Compatibility | ✅ | ⚠️ | ⚠️ | Use asyncio for library integration |
| Debugging Support | ✅ | ✅ | ⚠️ | Use asyncio for best debugging |

#### Performance Characteristics

| Backend | Memory Usage | Task Spawn Overhead | I/O Efficiency | Best For |
|---------|--------------|---------------------|----------------|----------|
| asyncio | Higher | Low | High | I/O-bound operations |
| trio | Lower | Low | High | Structured concurrency |
| curio | Lowest | Very Low | High | Low-level I/O operations |

### Migration Guide

#### Switching Backends

**Step 1: Install the Backend**
```bash
# For trio
uv pip install trio

# For curio
uv pip install curio
```

**Step 2: Set Environment Variable**
```bash
# Set backend via environment variable
export ANYIO_BACKEND=trio
# or
export ANYIO_BACKEND=curio
```

**Step 3: Test Your Code**
```bash
# Run tests with new backend
pytest tests/unit/ -v

# Test manually
python prdiffer/server.py
```

#### Backend-Specific Code

The codebase is designed to be backend-agnostic. However, if you need backend-specific functionality:

**Using asyncio-specific features**:
```python
import anyio

async def operation_with_asyncio_features():
    # Get the native backend
    backend = await anyio.current_time()  # Works with all backends

    # If you need asyncio-specific features:
    if anyio.current_backend().name == "asyncio":
        import asyncio
        # Use asyncio-specific features
        task = asyncio.current_task()
```

**Using trio-specific features**:
```python
import anyio

async def operation_with_trio_features():
    if anyio.current_backend().name == "trio":
        import trio
        # Use trio-specific features
        await trio.sleep(0)  # Checkpoint
```

### Recommended Configuration by Use Case

**Production Deployment (asyncio)**:
```bash
# Default configuration - no changes needed
python prdiffer/server.py
```

**Development/Testing (trio)**:
```bash
# Use trio for cleaner async semantics during development
export ANYIO_BACKEND=trio
python prdiffer/server.py
```

**High-Performance Low-Overhead (curio)**:
```bash
# Experimental: use curio for minimal overhead
export ANYIO_BACKEND=curio
python prdiffer/server.py
```

### Backend Compatibility Notes

**pytest-asyncio Integration**:
- Works seamlessly with asyncio backend (default)
- For trio, use `pytest-trio` instead of `pytest-asyncio`
- For curio, limited pytest support

**MCP Server Integration**:
- FastMCP uses asyncio internally
- Recommended to use asyncio backend for MCP server deployment
- Other backends may work but are not officially tested

**Testing with Different Backends**:
```bash
# Test with asyncio (default)
pytest tests/unit/ -v

# Test with trio
ANYIO_BACKEND=trio pytest tests/unit/ -v

# Test with curio
ANYIO_BACKEND=curio pytest tests/unit/ -v
```

### Troubleshooting

**Issue**: "Backend not found" error
```bash
# Solution: Install the backend
uv pip install trio  # or curio
```

**Issue**: Tests pass with asyncio but fail with trio
```bash
# Solution: Check for asyncio-specific code
# Look for direct imports of asyncio modules
grep -r "import asyncio" prdiffer/
grep -r "from asyncio" prdiffer/
```

**Issue**: Performance degradation with new backend
```bash
# Solution: Profile with different backends
python -m cProfile -o profile_trio.stats -c "import anyio; anyio.run(main, backend='trio')"
python -m cProfile -o profile_asyncio.stats -c "import anyio; anyio.run(main, backend='asyncio')"
```

## Related Documentation

- **Domain Layer**: `../domain/CLAUDE.md` - Domain entities, use cases, and interfaces
- **Application Layer**: `../application/CLAUDE.md` - MCP server and application components
- **GitHub Components**: `github/CLAUDE.md` - Modular GitHub API integration components
- **Security Components**: `security/CLAUDE.md` - Input validation and security features
- **Utility Components**: `utils/CLAUDE.md` - Retry, circuit breaker, and pattern matching utilities
- **Factory Implementation**: `factories/CLAUDE.md` - Dependency injection and service creation
- **Service Implementations**: `services/CLAUDE.md` - Concrete service implementations
- **Main Package**: `../CLAUDE.md` - Overall architecture and package structure
- **Testing**: `tests/unit/infrastructure/CLAUDE.md` - Infrastructure layer testing guide