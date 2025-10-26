# CLAUDE.md - Infrastructure Layer

This file provides guidance for working with the Infrastructure Layer of CCPRAgents.

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
- `[default]`, `[development]`, `[production]`, `[testing]` environments
- GitHub, MCP, cache, and application settings sections
- File filtering patterns and extensions

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