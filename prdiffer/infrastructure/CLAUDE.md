# CLAUDE.md - Infrastructure Layer

This file provides guidance for working with the Infrastructure Layer of PRDiffer.

**Current Version:** 0.4.7

## Infrastructure Layer Overview

The infrastructure layer contains external integrations, data access implementations, and cross-cutting concerns like settings and logging. This layer implements interfaces defined in the domain layer.

## Key Components

### GitHub Integration (`github_repository.py`)

**GitHubPRDiffRepository**
- Implements `PRDiffRepository` interface from domain layer
- Uses PyGithub library for GitHub API integration
- Handles authentication, rate limiting, and API error handling

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