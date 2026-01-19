# CLAUDE.md - GitHub Infrastructure Components

This file provides guidance for working with the GitHub infrastructure components of PRDiffer.

**Current Version:** 0.4.7

## Overview

This directory contains modular GitHub-related infrastructure components extracted from the original monolithic `GitHubPRDiffRepository` class. These components follow Clean Architecture principles with proper separation of concerns and dependency injection.

## Components

### API Client (`api_client.py`)

**GitHubAPIClient**
- Implements `GitHubAPIServiceInterface` from domain layer
- Handles GitHub authentication using PyGithub with personal access tokens
- Provides repository and pull request access with retry logic
- Includes file content retrieval with caching for performance

**Key Features:**
- **Lazy Initialization**: Client objects created only when needed
- **Retry Logic**: Exponential backoff with jitter for API failures
- **Caching**: File content cache to avoid repeated API calls
- **Error Handling**: Graceful fallbacks for missing files and rate limits

**Usage Pattern:**
```python
client = get_github_api_client(max_retries=3, retry_delay=1.0, timeout=30)
client.initialize_client(github_token="your_token")
repo = client.get_repository("owner/repo")
content = client.get_file_content(repo, "path/to/file.py", "branch")
```

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