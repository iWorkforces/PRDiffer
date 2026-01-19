# CLAUDE.md - Domain Config

This file provides guidance for working with the Domain Config module.

**Current Version:** 0.4.7

## Overview

The `domain/config/` module provides centralized configuration management for GitHub API interactions. It uses frozen dataclasses to create immutable, thread-safe configuration objects.

## Key Components

### GitHubConfig (`github_config.py`)

A frozen dataclass that centralizes all GitHub-related settings in a single source of truth.

**Key Features:**
- **Immutable**: Frozen dataclass prevents accidental modifications
- **Type-Safe**: All fields are typed for better IDE support
- **Thread-Safe**: Immutability enables safe concurrent access
- **Single Source**: One place to manage all GitHub settings

**Configuration Categories:**

1. **Basic API Settings**
   - `rate_limit`: Maximum API requests per hour (default: 5000)
   - `timeout`: Request timeout in seconds (default: 30)
   - `max_retries`: Maximum retry attempts (default: 3)
   - `retry_delay`: Base delay between retries (default: 1.0)

2. **Smart Retry Settings**
   - `retry_on_404`: Don't retry 404 errors (default: False)
   - `retry_on_403`: Retry 403 errors (might be rate limiting, default: True)
   - `retry_on_500`: Retry 5xx server errors (default: True)
   - `retry_log_level`: Log level for retry attempts (default: "DEBUG")
   - `permanent_failure_log_level`: Log level for permanent failures (default: "INFO")

3. **Circuit Breaker & Adaptive Retry**
   - `circuit_breaker_enabled`: Enable circuit breaker pattern (default: True)
   - `circuit_breaker_failure_threshold`: Failures before opening circuit (default: 5)
   - `circuit_breaker_timeout`: Seconds to keep circuit open (default: 60)
   - `adaptive_retry_enabled`: Enable adaptive retry delays (default: True)
   - `max_adaptive_delay`: Maximum adaptive delay in seconds (default: 30)
   - `api_health_tracking`: Track API health metrics (default: True)
   - `context_aware_retry`: Enable context-aware retry strategies (default: True)

4. **File Filtering Patterns**
   - `ignore_patterns`: Tuple of patterns to ignore (for hashability)
   - `valid_extensions`: Tuple of valid file extensions (for hashability)

5. **Parallel Diff Processing**
   - `diff_parallel_enabled`: Enable parallel diff generation (default: True)
   - `diff_parallel_threshold`: Minimum files to trigger parallel processing (default: 3)
   - `diff_max_workers`: Maximum worker threads (default: 4)
   - `diff_worker_timeout`: Timeout per file in seconds (default: 30.0)

6. **File Processing Limits**
   - `max_files_allowed`: Maximum files to process per PR (default: 50)

## Usage Patterns

### Creating Configuration

```python
from prdiffer.domain.config import GitHubConfig

# Create with defaults
config = GitHubConfig()

# Create from dictionary
settings = {
    "rate_limit": 10000,
    "timeout": 60,
    "ignore_patterns": ["*.lock", "node_modules/"]
}
config = GitHubConfig.from_dict(settings)

# Create with overrides
config = GitHubConfig(rate_limit=10000, timeout=60)
```

### Using Helper Methods

```python
# Check circuit breaker
if config.should_use_circuit_breaker:
    # Enable circuit breaker logic
    pass

# Check parallel processing
if config.should_use_parallel_diff:
    # Use parallel diff generation
    pass

# File validation
if config.should_process_file("src/main.py"):
    # Process the file
    pass

# Check file ignore patterns
if config.should_ignore_file("node_modules/index.js"):
    # Skip this file
    pass

# Check file extension
if config.has_valid_extension("src/main.py"):
    # File has valid extension
    pass
```

### Creating Variants

```python
# Create modified config
new_config = config.with_overrides(
    rate_limit=10000,
    timeout=60
)
```

## Configuration Source

Configuration is typically loaded from `settings.toml` and converted to `GitHubConfig` via the `SettingsService`.

**Example `settings.toml`:**
```toml
[default]
github.rate_limit = 5000
github.timeout = 30
github.max_retries = 3
github.retry_delay = 1

github.retry_on_404 = false
github.retry_on_403 = true
github.retry_on_500 = true

github.circuit_breaker_enabled = true
github.circuit_breaker_failure_threshold = 5
github.circuit_breaker_timeout = 60

github.ignore_patterns = ["*.lock", "node_modules/"]
github.valid_extensions = [".py", ".js", ".ts", ".md"]

github.diff_parallel_enabled = true
github.diff_parallel_threshold = 3
github.diff_max_workers = 4
github.diff_worker_timeout = 30.0
```

## Design Decisions

### Why Frozen Dataclass?
- Prevents accidental modification after creation
- Enables safe concurrent access without locks
- Makes configuration changes explicit (via `with_overrides()`)

### Why Tuples for Patterns?
- Tuples are hashable (lists are not)
- Enables use as dictionary keys or in sets
- Immutability prevents runtime changes

### Why Helper Methods?
- Encapsulates complex logic (e.g., file pattern matching)
- Provides readable intent (e.g., `should_use_circuit_breaker`)
- Allows changing implementation without affecting callers

## Integration Points

**Settings Service**: Creates `GitHubConfig` from `settings.toml`
**GitHub API Client**: Receives `GitHubConfig` for all GitHub settings
**File Processor**: Uses `should_process_file()` for filtering
**Diff Generator**: Checks `should_use_parallel_diff()` for parallel processing

## Thread Safety

`GitHubConfig` is frozen (immutable), making it inherently thread-safe:
- Multiple threads can safely read the same instance
- No locks needed for concurrent access
- `with_overrides()` creates new instances rather than modifying existing ones
