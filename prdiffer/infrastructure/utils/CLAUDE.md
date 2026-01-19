# CLAUDE.md - Infrastructure Utilities

This file provides guidance for working with the infrastructure utilities of PRDiffer.

**Current Version:** 0.4.7

## Overview

This directory contains general-purpose utility components that support the main GitHub repository implementation. These utilities are designed to be reusable, testable, and follow Clean Architecture principles with proper domain interfaces.

## Utility Components

### Retry Handler (`retry_handler.py`)

**RetryHandler**
- Implements `RetryServiceInterface` from domain layer
- Provides configurable retry logic with exponential backoff and jitter
- Handles rate limit detection and appropriate retry strategies
- Comprehensive logging for debugging retry attempts

**Key Features:**
- **Exponential Backoff**: Progressively increasing delays between retries
- **Jitter**: Random variation to prevent thundering herd problems
- **Rate Limit Detection**: Special handling for GitHub API rate limits
- **Configurable Parameters**: Max retries, base delay, and timeout settings

**Usage Pattern:**
```python
retry_handler = get_retry_handler(max_retries=3, retry_delay=1.0)
result = retry_handler.execute_with_retry(some_function, arg1, arg2, keyword=value)
```

**Retry Strategy:**
- **Attempt 1**: Immediate execution
- **Attempt 2**: Base delay (1s) + jitter
- **Attempt 3**: 2 × base delay (2s) + jitter
- **Final Attempt**: 4 × base delay (4s) + jitter, then raise exception

### Pattern Matcher (`pattern_matcher.py`)

**PatternMatcher**
- Implements `PatternMatchingServiceInterface` from domain layer
- Efficient file filtering using pre-compiled regex patterns
- Supports wildcards, directory patterns, and exact matches
- Validates files against ignore patterns and valid extensions

**Pattern Types Supported:**
- **Exact Matches**: `filename.ext` matches exactly
- **Wildcard Extensions**: `*.lock` matches all `.lock` files
- **Directory Patterns**: `node_modules/` matches entire directories
- **Complex Wildcards**: `temp-*-files` with regex compilation
- **Valid Extensions**: Whitelist of allowed file types

**Configuration:**
```python
matcher = get_pattern_matcher(
    ignore_patterns=['*.lock', 'node_modules/', 'temp-*'],
    valid_extensions=['.py', '.js', '.ts', '.md']
)
is_valid = matcher.is_valid_file('src/main.py')  # True
is_valid = matcher.is_valid_file('package.lock')  # False
```

**Performance Optimizations:**
- **Pre-compilation**: Regex patterns compiled once during initialization
- **Pattern Classification**: String patterns vs regex patterns for optimal matching
- **Early Termination**: Short-circuit evaluation on first match

### Diff Utils (`diff_utils.py`)

**DiffUtils**
- Implements `DiffServiceInterface` from domain layer
- Core diff generation using Python's `difflib` module
- Content encoding detection and conversion utilities
- Patch extension for full-file context display

**Key Capabilities:**
- **Full-File Patches**: Generate complete file context diffs
- **Content Decoding**: Handle various text encodings (UTF-8, ISO-8859-1, Latin-1, ASCII, UTF-16)
- **Patch Extension**: Convert minimal patches to full-file context
- **Hunk Header Parsing**: Extract line numbers and change ranges
- **Content Normalization**: Standardize line endings and whitespace

**Diff Generation Process:**
1. **Content Preparation**: Decode and normalize file content
2. **Sequence Matching**: Use `difflib.SequenceMatcher` for line comparison
3. **Hunk Creation**: Generate unified diff format with proper headers
4. **Context Addition**: Include full file context for better analysis

**Output Format:**
```
@@ -1,10 +1,12 @@
 line1
 line2
-removed_line
+added_line
 line4
+another_added_line
 line5
```

### Circuit Breaker (`circuit_breaker.py`)

**CircuitBreaker**
- Implements `CircuitBreakerServiceInterface` from domain layer
- Prevents cascading failures by temporarily disabling failing operations
- Configurable failure thresholds and reset timeouts
- State management with open, half-open, and closed states

**Key Features:**
- **Failure Detection**: Tracks consecutive failures and error rates
- **Automatic Recovery**: Automatically resets after successful operations
- **Configurable Thresholds**: Customizable failure count and timeout settings
- **State Monitoring**: Tracks circuit state transitions for observability

**Usage Pattern:**
```python
circuit_breaker = get_circuit_breaker(failure_threshold=5, reset_timeout=60)
result = circuit_breaker.execute(risky_operation, arg1, arg2)
```

**Circuit States:**
- **Closed**: Normal operation, all requests pass through
- **Open**: Circuit open, all requests fail fast
- **Half-Open**: Testing if service has recovered

### API Health Tracker (`api_health_tracker.py`)

**APIHealthTracker**
- Implements `APIHealthServiceInterface` from domain layer
- Monitors API performance metrics and error rates
- Tracks response times, success rates, and failure patterns
- Provides health status and performance insights

**Key Features:**
- **Performance Metrics**: Response time tracking and statistics
- **Error Rate Monitoring**: Failure rate calculation and trend analysis
- **Health Status**: Overall API health assessment
- **Historical Data**: Performance history for trend analysis

**Metrics Tracked:**
- **Response Times**: Average, p95, p99 response times
- **Success Rate**: Percentage of successful operations
- **Error Rates**: Breakdown by error type and frequency
- **Throughput**: Operations per minute/second

### Cache Decorator (`cache_decorator.py`)

**CachingMixin & Decorators**
- Provides method-level caching with support for unhashable parameters
- No domain interface (general-purpose utility, not domain-specific)
- Handles complex object types that can't be cached with standard `@lru_cache`
- TTL support with automatic expiration and LRU eviction
- **Thread-safe with reentrant lock protection**

**Key Components:**

1. **CachingMixin** - Base class for adding caching capabilities
   - Configurable cache size limit (default: 1000 entries)
   - Configurable default TTL (default: 300 seconds = 5 minutes)
   - Cache statistics tracking (hits, misses, hit rate)
   - Automatic cleanup of expired entries
   - LRU eviction when cache size limit is reached
   - **Thread-safe with `threading.RLock()`**

2. **@cached_method** decorator - Caches method results with TTL
   - Automatic conversion of unhashable types to hashable forms
   - Handles lists, dicts, sets, and custom objects
   - Circular reference detection and protection
   - Configurable TTL per method
   - Optional key prefix for cache namespacing
   - Individual method cache clearing support
   - **All operations protected by reentrant lock**

3. **@conditional_cache** decorator - Conditional caching
   - Only caches results that meet specific criteria
   - Example: Cache only non-None results
   - Useful for operations that may fail or return invalid data
   - **Thread-safe conditional caching**

**Thread Safety Guarantees**:

- **Reentrant Lock**: `threading.RLock()` protects all cache operations
- **Atomic Operations**: All cache reads/writes under lock protection
- **Safe Cleanup**: `clear_method_cache()` properly locked
- **Statistics Safety**: Hit/miss counters updated atomically

**Thread-Safe Usage Pattern:**

```python
from prdiffer.infrastructure.utils.cache_decorator import CachingMixin, cached_method

class MyService(CachingMixin):
    def __init__(self):
        super().__init__(max_cache_size=500, default_ttl=600)
        # _cache_lock (RLock) automatically initialized

    @cached_method(ttl=300)
    def expensive_operation(self, params: List[str]) -> str:
        # Thread-safe: multiple threads can safely access
        return do_expensive_work(params)

    # Thread-safe cache clearing
    def clear_all_caches(self):
        self.clear_method_cache()  # Protected by lock
```

**Thread Safety Implementation:**

```python
class CachingMixin:
    def __init__(self, max_cache_size: int = 1000, default_ttl: int = 300):
        # Thread safety lock for cache operations
        self._cache_lock = threading.RLock()
        self._method_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def _get_cached_value(self, cache_key: str):
        # Thread-safe cache lookup
        with self._cache_lock:
            if cache_key in self._method_cache:
                entry = self._method_cache[cache_key]
                if not self._is_expired(entry):
                    self._cache_hits += 1
                    return entry["value"]
                else:
                    del self._method_cache[cache_key]
            self._cache_misses += 1
            return None

    def _set_cached_value(self, cache_key: str, value, ttl: int):
        # Thread-safe cache update
        with self._cache_lock:
            self._method_cache[cache_key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }
            self._enforce_max_size()

    def clear_method_cache(self):
        # Thread-safe cache clearing
        with self._cache_lock:
            self._method_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
```

**Unhashable Parameter Handling:**
The cache decorator solves the common problem where `@lru_cache` fails with unhashable types:
- **Lists** → Converted to tuples
- **Dicts** → Converted to sorted tuples of key-value pairs
- **Sets** → Converted to sorted tuples
- **Custom Objects** → Uses type name and ID
- **Circular References** → Detected and handled safely

**Usage Pattern:**
```python
from prdiffer.infrastructure.utils.cache_decorator import CachingMixin, cached_method

class MyService(CachingMixin):
    def __init__(self):
        super().__init__(max_cache_size=500, default_ttl=600)

    @cached_method(ttl=300)
    def expensive_operation(self, params: List[str]) -> str:
        # Lists are automatically converted to tuples for caching
        return do_expensive_work(params)

    @conditional_cache(lambda result: result is not None, ttl=600)
    def maybe_expensive(self, key: str) -> Optional[str]:
        # Only cache non-None results
        return might_return_none(key)
```

**Cache Statistics:**
```python
service = MyService()
stats = service.get_cache_stats()
# Returns: {
#   "size": 42,
#   "hits": 120,
#   "misses": 30,
#   "hit_rate": 0.8,
#   "total_requests": 150,
#   "max_size": 500,
#   "default_ttl": 600
# }
```

**Use Cases:**
- Settings service with Dynaconf objects (unhashable)
- GitHub API responses with complex nested structures
- Configuration values containing lists or dicts
- Expensive computations with mutable parameters
- Methods that receive unhashable objects as parameters

**Performance Benefits:**
- Avoids repeated expensive computations
- Reduces GitHub API calls for unchanged data
- Automatic cleanup prevents memory leaks
- LRU eviction keeps memory usage bounded
- TTL ensures data freshness

## Architecture Integration

### Dependency Flow
```
GitHubPRDiffRepository
    ├── RetryHandler ← GitHub API operations
    ├── PatternMatcher ← File filtering
    └── DiffUtils ← Patch generation
```

### Domain Interface Compliance
Most utilities implement domain service interfaces:
- `RetryHandler` → `RetryServiceInterface`
- `PatternMatcher` → `PatternMatchingServiceInterface`
- `DiffUtils` → `DiffServiceInterface`
- `CircuitBreaker` → `CircuitBreakerServiceInterface`
- `APIHealthTracker` → `APIHealthServiceInterface`
- `CacheDecorator` → No domain interface (general-purpose utility)

### Factory Pattern
Each utility provides a factory function for easy instantiation:
```python
# Get configured instances
retry_handler = get_retry_handler()
pattern_matcher = get_pattern_matcher(ignore_patterns, valid_extensions)
diff_utils = get_diff_utils()
circuit_breaker = get_circuit_breaker()
health_tracker = get_api_health_tracker()
```

## Development Guidelines

### Adding New Utilities

1. **Create Domain Interface**: Define contract in `prdiffer/domain/services/`
2. **Implement Utility**: Create implementation in this directory
3. **Add Factory Function**: Provide `get_*` factory for easy instantiation
4. **Update __init__.py**: Export new utility and factory function
5. **Write Tests**: Create comprehensive unit tests

### Configuration Patterns
Utilities should accept configuration through:
- **Constructor Parameters**: Direct configuration for testing
- **Settings Service**: Production configuration from settings files
- **Environment Variables**: Runtime overrides when needed

### Error Handling Standards
- **Graceful Degradation**: Return sensible defaults instead of crashing
- **Comprehensive Logging**: Log errors with context for debugging
- **Exception Propagation**: Let critical errors bubble up appropriately
- **Input Validation**: Validate inputs and provide clear error messages

### Performance Considerations
- **Lazy Initialization**: Create expensive resources only when needed
- **Caching**: Cache compiled patterns and expensive computations
- **Memory Management**: Clear caches and resources appropriately
- **Algorithmic Efficiency**: Choose optimal algorithms for the use case

## Testing Strategies

### Unit Testing
Each utility should have comprehensive unit tests covering:
- **Normal Operation**: Basic functionality with valid inputs
- **Edge Cases**: Empty inputs, boundary conditions, unusual patterns
- **Error Conditions**: Invalid inputs, network failures, encoding issues
- **Performance**: Verify acceptable performance with large datasets

### Integration Testing
Test utilities working together:
- **Retry + API Calls**: Test retry behavior with actual GitHub API
- **Pattern + File Lists**: Test filtering with real file structures
- **Diff + File Content**: Test patch generation with actual file changes

### Mock Testing
Use mocks for external dependencies:
- **Network Calls**: Mock API responses for retry testing
- **File System**: Mock file operations for pattern testing
- **Heavy Operations**: Mock expensive computations for faster tests

## File Organization

```
prdiffer/infrastructure/utils/
├── __init__.py              # Public API exports
├── retry_handler.py         # Exponential backoff retry logic
├── pattern_matcher.py       # File pattern matching utilities
├── diff_utils.py           # Diff generation and content utilities
├── circuit_breaker.py      # Circuit breaker pattern implementation
├── api_health_tracker.py   # API performance monitoring
└── cache_decorator.py      # Method-level caching with unhashable parameter support
```

## Common Use Cases

### GitHub API Reliability
```python
retry_handler = get_retry_handler(max_retries=5, retry_delay=2.0)
def fetch_with_retry():
    return retry_handler.execute_with_retry(api_client.get_repository, "owner/repo")
```

### File Filtering
```python
pattern_matcher = get_pattern_matcher(
    ignore_patterns=['*.log', 'tmp/', '*.cache'],
    valid_extensions=['.py', '.md', '.yml']
)
valid_files = [f for f in all_files if pattern_matcher.is_valid_file(f)]
```

### Patch Generation
```python
diff_utils = get_diff_utils()
patch = diff_utils.build_full_file_patch(original_content, modified_content)
extended_patch = diff_utils.extend_patch(original_content, minimal_patch, modified_content)
```

### Circuit Breaker Protection
```python
circuit_breaker = get_circuit_breaker(failure_threshold=3, reset_timeout=30)
health_tracker = get_api_health_tracker()

# Protected operation
result = circuit_breaker.execute(
    lambda: api_client.make_request(),
    context={"operation": "github_api_call"}
)

# Monitor health
health_status = health_tracker.get_health_status()
```

## Migration Notes

These utilities were extracted from the original monolithic `GitHubPRDiffRepository` class to:
- **Improve Testability**: Each utility can be tested in isolation
- **Enable Reusability**: Utilities can be used by other components
- **Reduce Complexity**: Main repository class focuses on orchestration
- **Follow SOLID Principles**: Single responsibility for each utility

The extraction maintained 100% backward compatibility while dramatically improving code organization and maintainability.