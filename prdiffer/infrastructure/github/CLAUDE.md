# CLAUDE.md - GitHub Infrastructure Components

This file provides guidance for working with the GitHub infrastructure components of PRDiffer.

**Current Version:** 0.4.8

## Overview

This directory contains modular GitHub-related infrastructure components extracted from the original monolithic `GitHubPRDiffRepository` class. These components follow Clean Architecture principles with proper separation of concerns and dependency injection.

## Components

### API Client (`api_client.py`)

**GitHubAPIClient**
- Implements `GitHubAPIServiceInterface` from domain layer
- Handles GitHub authentication using PyGithub with personal access tokens
- Provides repository and pull request access with retry logic
- Includes file content retrieval with caching for performance

**Public Methods:**

**Initialization:**
- `initialize_client(github_token: str, timeout: int)`: Initialize the PyGithub client
  - Creates authenticated GitHub client instance
  - Sets timeout for API operations
  - Must be called before other methods

**Repository Access:**
- `get_repository(repo_full_name: str) -> Repository`: Get repository object by full name
  - Returns PyGithub Repository object
  - Format: "owner/repo"
  - Raises `UnknownObjectException` if not found

- `get_pull_request(repository: Repository, pr_number: int) -> PullRequest`: Get PR object
  - Returns PyGithub PullRequest object
  - Raises `UnknownObjectException` if not found

**File Content Methods:**
- `get_file_content(repository, file_path: str, branch: str) -> str`: Get single file content
  - Returns file content as string
  - Empty string if file not found

- `get_files_content_batch(repository, file_paths: List[str], branch: str) -> Dict[str, str]`: Batch file content retrieval
  - Returns dict mapping file_path -> content
  - More efficient than individual calls

**Cache Management:**
- `clear_cache()`: Clear all cached file content
  - Resets both memory cache and metadata
  - Useful for testing or forced refresh

- `get_cache_stats() -> Dict[str, Any]`: Get cache statistics
  - Returns dict with cache performance metrics:
    - `hits`: Number of cache hits
    - `misses`: Number of cache misses
    - `hit_rate`: Cache hit rate (0.0-1.0)
    - `size`: Current cache size
    - `ttl`: Cache time-to-live in seconds

**Async Methods (Internal):**
- `_get_file_content_async()`: Async version of get_file_content
- `_get_files_content_batch_parallel_async()`: Parallel async batch retrieval

**Usage Pattern:**
```python
client = get_github_api_client(max_retries=3, retry_delay=1.0, timeout=30)
client.initialize_client(github_token="your_token")
repo = client.get_repository("owner/repo")
content = client.get_file_content(repo, "path/to/file.py", "branch")

# Check cache performance
stats = client.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
```

**Key Features:**
- **Lazy Initialization**: Client objects created only when needed
- **Retry Logic**: Exponential backoff with jitter for API failures
- **Caching**: File content cache to avoid repeated API calls
- **Error Handling**: Graceful fallbacks for missing files and rate limits

### File Processor (`file_processor.py`)

**FileProcessor**
- Handles file filtering, content loading, and parallel processing
- Integrates with pattern matching and GitHub API services
- Provides batch processing capabilities for better performance
- Manages file content limits to respect GitHub API rate limits
- **Thread-safe with double-check locking**

**Key Features:**
- **Pattern-Based Filtering**: Uses `PatternMatchingServiceInterface` for file validation
- **Batch Processing**: Efficient bulk file content retrieval
- **Parallel Processing**: Thread pool execution for concurrent file processing
- **Content Limiting**: Respects `max_files_allowed` setting to avoid rate limits
- **Thread Safety**: PR files cache protected with reentrant lock

**Public Methods:**

**File Retrieval:**
- `get_pr_files(pull_request) -> PaginatedList[File]`: Get all files from PR with caching
  - Returns PyGithub PaginatedList of File objects
  - Uses thread-safe caching with 5-minute TTL
  - Double-check locking pattern for performance
  - Cache key: PullRequest object identity

- `filter_files(files, ignore_patterns, valid_extensions) -> List[File]`: Filter files by patterns
  - Returns list of filtered File objects
  - Applies ignore patterns (wildcards supported)
  - Validates file extensions against whitelist
  - Returns empty list if no files match

**Patch Processing:**
- `process_files_to_patches(repository, files, base_sha, head_sha) -> Dict[str, FilePatchInfo]`: Process files to patches (sync)
  - Returns dict mapping filename -> FilePatchInfo
  - Loads full file content for all files
  - Generates unified diffs with full context
  - Gracefully degrades when file count exceeds limit

- `process_files_to_patches_async(repository, files, base_sha, head_sha) -> Dict[str, FilePatchInfo]`: Async patch processing
  - Same as sync version but uses async parallel execution
  - Better performance for large PRs
  - Uses AsyncParallelExecutor for concurrent operations
  - Returns same data structure as sync version

**Internal Processing Methods:**
- `_process_files_with_content_parallel_async()`: Parallel async file processing with content loading
  - Processes multiple files concurrently using anyio task groups
  - Respects max_files_allowed limit from settings
  - Falls back to patch-only mode when limit exceeded
  - Thread-safe with proper error handling

- `_create_file_patch_with_content()`: Creates FilePatchInfo with full content
  - Generates unified diff with base and head content
  - Handles rename-only files (no content needed)
  - Calculates statistics (additions, deletions)
  - Returns None for binary files or errors

- `_generate_patch_from_content()`: Generates unified diff from file contents
  - Uses difflib.unified_diff for patch generation
  - Handles multiple encoding attempts (UTF-8, latin-1, etc.)
  - Returns empty string for binary files
  - Includes full file context (not minimal hunks)

- `_is_rename_only()`: Detects rename-only changes
  - Checks status for RENAMED status code (R[0-9]+)
  - Returns True if file was renamed without content changes
  - Used to skip content loading for renames

**Thread Safety Implementation**:

- **Double-Check Locking**: Fast path cache check without lock, slow path with lock
- **Cache Lock**: `_cache_lock` (threading.RLock) protects PR files cache
- **Atomic Initialization**: Cache initialization and updates are thread-safe
- **Race Condition Fixed**: Fixed race condition in `get_pr_files()` method

**Thread-Safe Pattern:**

```python
def get_pr_files(self, pull_request) -> PaginatedList[File]:
    # Fast path: check cache without lock (double-check pattern)
    if self._pr_files_cache is not None:
        current_time = time.time()
        if current_time - self._pr_cache_timestamp <= 300:
            return self._pr_files_cache

    # Slow path: acquire lock and double-check
    with self._cache_lock:
        # Double-check cache validity after acquiring lock
        if self._pr_files_cache is not None:
            current_time = time.time()
            if current_time - self._pr_cache_timestamp <= 300:
                return self._pr_files_cache

        # Initialize cache under lock protection
        self._pr_files_cache = pull_request.get_files()
        self._pr_cache_timestamp = time.time()
        return self._pr_files_cache
```

**Processing Modes:**
- **Sequential**: Standard processing with content loading
- **Batch**: Bulk content retrieval for better API efficiency
- **Parallel**: Concurrent processing using ThreadPoolExecutor
- **Limited**: Graceful degradation when file count exceeds limits

### Diff Generator (`diff_generator.py`)

**DiffGenerator**
- Creates extended diff output with full file context
- Processes patch hunks and adds line number formatting
- Handles commit message retrieval and formatting
- Supports both simple and line-numbered diff formats

**Key Features:**
- **Extended Patches**: Full file context instead of minimal hunks
- **Hunk Processing**: Line-by-line diff analysis with proper formatting
- **Line Numbers**: Optional line number addition to diff hunks
- **Commit Integration**: Retrieval and formatting of commit messages

**Diff Formats:**
- **Standard**: File headers with extended patch content
- **Line Numbered**: Hunks with line numbers for better readability
- **Full Context**: Complete file content showing all changes

### Parallel Executor (`parallel_executor.py`)

**ParallelExecutor**
- General-purpose parallel execution utility
- Thread pool management for concurrent operations
- Support for different execution patterns (batch, mapped, contextual)
- Configurable worker counts and timeouts

**Execution Patterns:**
- **Batch Processing**: Apply function to list of items in parallel
- **Context-Based**: Shared context passed to all parallel operations
- **Mapped Execution**: Different functions for different item types
- **Timeout Management**: Configurable timeouts for individual operations

## Architecture Integration

### Dependency Flow
```
GitHubPRDiffRepository (Main Class)
    ├── GitHubAPIClient (API interactions)
    │   ├── RetryHandler (retry logic)
    │   ├── CircuitBreaker (failure protection)
    │   └── APIHealthTracker (performance monitoring)
    ├── FileProcessor (file operations)
    │   ├── PatternMatcher (filtering)
    │   ├── DiffUtils (utilities)
    │   ├── GitHubAPIClient (content loading)
    │   └── ParallelExecutor (concurrent processing)
    ├── DiffGenerator (output formatting)
    │   └── DiffUtils (patch processing)
    └── ParallelExecutor (optional, for performance)
```

### Interface Compliance
All components implement domain interfaces:
- `GitHubAPIClient` → `GitHubAPIServiceInterface`
- Components use dependency injection for testability
- Factory functions provide configured instances

### Configuration Sources
Components receive configuration from:
- **Settings Service**: GitHub API settings, rate limits, timeouts
- **Constructor Parameters**: Custom overrides for testing
- **Environment Variables**: GitHub tokens, authentication

## Development Guidelines

### Adding New GitHub Features
1. **Identify Component**: Determine which component handles the functionality
2. **Update Interface**: Add method to appropriate domain interface
3. **Implement Method**: Add implementation to infrastructure component
4. **Update Factory**: Ensure proper initialization in factory functions
5. **Test Integration**: Verify component works with main repository class

### Performance Considerations
- **API Rate Limits**: Use batch processing and caching where possible
- **Parallel Processing**: Leverage `ParallelExecutor` for independent operations
- **Memory Usage**: Clear caches periodically in long-running processes
- **Network Timeouts**: Configure appropriate timeouts for GitHub API calls
- **Circuit Protection**: Use circuit breaker to prevent cascading failures during outages
- **Health Monitoring**: Track API performance to detect degradation early
- **Retry Optimization**: Use advanced retry strategies with health-aware backoff

### Error Handling Patterns
- **Graceful Degradation**: Return empty results instead of failing
- **Retry Logic**: Use exponential backoff with jitter for transient failures
- **Circuit Breaker**: Prevent cascading failures by temporarily disabling failing operations
- **Health Tracking**: Monitor error rates and performance degradation
- **Cache Failures**: Cache failed requests to avoid repeated calls during outages
- **Logging**: Comprehensive logging with context for debugging and monitoring
- **Fallback Strategies**: Provide alternative data sources when primary API fails

### Testing Strategies
- **Unit Tests**: Test each component in isolation with mocked dependencies
- **Integration Tests**: Test component interactions with GitHub API
- **Factory Tests**: Verify factory functions create properly configured instances
- **Error Scenarios**: Test rate limiting, network failures, and invalid responses
- **Circuit Tests**: Verify circuit breaker state transitions and recovery
- **Performance Tests**: Validate parallel processing and batch operations
- **Health Tests**: Test health tracking and monitoring functionality

## File Organization

```
prdiffer/infrastructure/github/
├── __init__.py              # Public API exports
├── api_client.py           # GitHub API wrapper
├── file_processor.py       # File operations and processing
├── diff_generator.py       # Diff creation and formatting
└── parallel_executor.py    # Concurrent execution utilities
```

## Migration Notes

When the original `GitHubPRDiffRepository` was refactored:
- **972 lines** reduced to **~200 lines** in main class
- **7 components** extracted with single responsibilities
- **100% backward compatibility** maintained
- **All existing functionality** preserved through composition
- **Enhanced reliability** with circuit breaker and health monitoring
- **Improved performance** with parallel processing and batch operations
- **Better testability** with dependency injection and interface contracts

This modular architecture improves maintainability, testability, reliability, and allows independent development of GitHub-related features while providing robust error handling and performance optimizations.