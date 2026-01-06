# CLAUDE.md - Unit Tests: Infrastructure

This file provides guidance for working with unit tests for infrastructure components.

## Overview

Unit tests for infrastructure verify the correctness of implementations that integrate with external systems (GitHub API, file system, caching, etc.).

## Test Structure

```
tests/unit/infrastructure/
├── CLAUDE.md                    # This file
├── conftest.py                  # Shared fixtures
├── test_github_repository.py   # Tests for GitHubPRDiffRepository
├── test_settings.py            # Tests for Settings service
├── test_cache_service.py       # Tests for CacheService
├── test_request_coalescing.py  # Tests for RequestCoalescingService
├── test_async_parallel_executor.py  # Tests for AsyncParallelExecutor
├── github/                     # GitHub component tests
│   ├── test_api_client.py      # Tests for APIClient
│   ├── test_diff_generator.py  # Tests for DiffGenerator
│   ├── test_file_processor.py  # Tests for FileProcessor
│   └── test_parallel_executor.py  # Tests for ParallelExecutor
├── utils/                      # Utility tests
│   ├── test_retry_handler.py   # Tests for RetryHandler
│   ├── test_pattern_matcher.py # Tests for PatternMatcher
│   ├── test_diff_utils.py      # Tests for DiffUtils
│   ├── test_circuit_breaker.py # Tests for CircuitBreaker
│   └── test_cache_decorator.py # Tests for CacheDecorator
├── logging/                    # Logging tests
│   └── test_console_logger.py  # Tests for ConsoleLogger
└── security/                   # Security tests
    └── test_input_validator.py # Tests for InputValidator
```

## Writing Tests

### Test Structure

```python
"""Unit tests for [infrastructure component]."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from ccpragents.infrastructure import [Component]

class Test[Component]:
    """Unit tests for [Component]."""

    @pytest.fixture
    def component(self, mock_dependencies):
        """Create component instance for testing."""
        return [Component](**mock_dependencies)

    def test_[feature](self, component):
        """Test [feature] works correctly."""
        # Arrange
        test_data = {...}

        # Act
        result = component.[method](test_data)

        # Assert
        assert result == expected
```

### Best Practices

1. **Mock External Calls**: Mock GitHub API, file I/O, network calls
2. **Test Error Handling**: Verify proper error handling
3. **Test Retry Logic**: Verify retries work correctly
4. **Test Caching**: Verify cache behavior
5. **Test Thread Safety**: For concurrent operations

## Running Tests

### Run All Infrastructure Tests
```bash
# Using pytest
pytest tests/unit/infrastructure/ -v

# Using unittest script
./start-unittest.sh --run tests/unit/infrastructure/
```

### Run Specific Test Directory
```bash
# Using pytest
pytest tests/unit/infrastructure/github/ -v

# Using unittest script
./start-unittest.sh --run tests/unit/infrastructure/github/
```

## Component-Specific Testing

### GitHubPRDiffRepository
Test the main GitHub repository implementation:
- **PR Diff Retrieval**: Get PR diff with correct format
- **Caching**: Verify commit-based caching
- **Error Handling**: API errors, network failures
- **File Filtering**: Ignore patterns and valid extensions
- **Rate Limiting**: Respect rate limits

### GitHub Components

#### APIClient
- **Authentication**: Token-based auth
- **Request Handling**: GET/POST requests
- **Error Handling**: API errors
- **Rate Limiting**: Handle rate limits

#### DiffGenerator
- **Diff Generation**: Create unified diffs
- **File Context**: Full file context diffs
- **Encoding**: Handle multiple encodings

#### FileProcessor
- **File Validation**: Check if file should be processed
- **Pattern Matching**: Apply ignore patterns
- **Extension Check**: Validate file extensions

#### ParallelExecutor
- **Parallel Processing**: Concurrent file processing
- **Error Collection**: Collect errors from parallel tasks
- **Timeout**: Handle worker timeouts

### Utility Components

#### RetryHandler
- **Exponential Backoff**: Increasing delays
- **Jitter**: Randomize retry delays
- **Max Retries**: Respect retry limits
- **Permanent Failures**: Detect permanent errors

#### PatternMatcher
- **Wildcard Matching**: * and ** patterns
- **Case Sensitivity**: Configurable case handling
- **Performance**: Efficient pattern matching

#### DiffUtils
- **Diff Parsing**: Parse unified diff format
- **Patch Extension**: Extend patches with context
- **Encoding Detection**: Detect file encodings

#### CircuitBreaker
- **Circuit States**: Open, closed, half-open
- **Failure Threshold**: Open after failures
- **Recovery**: Close after success
- **Timeout**: Reset timeout

#### CacheDecorator
- **Caching**: Cache method results
- **TTL**: Time-to-live expiration
- **LRU**: Least-recently-used eviction
- **Unhashable Parameters**: Handle lists/dicts

### Async Components

#### RequestCoalescingService
- **Request Deduplication**: Prevent duplicate requests
- **Waiter Management**: Track waiting requests
- **Timeout**: Handle timeout
- **Result Sharing**: Share results among waiters

#### AsyncParallelExecutor
- **Task Groups**: Use anyio task groups
- **Error Strategies**: IGNORE, RAISE, COLLECT, CONTINUE
- **Semaphore**: Concurrency control
- **Progress Tracking**: Track progress

### Logging Component

#### ConsoleLogger
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Formatting**: Structured logging
- **Colors**: ANSI color codes
- **Context**: Include context in logs

### Security Component

#### InputValidator
- **URL Validation**: GitHub URL format validation
- **Injection Prevention**: Detect and block injection attempts
- **Repository Validation**: Validate owner/repo names
- **String Sanitization**: Sanitize user input

## Test Fixtures

Create reusable fixtures in `conftest.py`:

```python
# tests/unit/infrastructure/conftest.py

import pytest
from unittest.mock import Mock, AsyncMock
import httpx

@pytest.fixture
def mock_github_client():
    """Mock GitHub API client."""
    client = Mock()
    client.get_repo = Mock()
    client.get_pull = Mock()
    return client

@pytest.fixture
def mock_response():
    """Mock HTTP response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json = Mock(return_value={"data": "test"})
    response.text = "response text"
    return response

@pytest.fixture
def mock_settings():
    """Mock settings service."""
    settings = Mock()
    settings.get = Mock(return_value="default_value")
    return settings

@pytest.fixture
def mock_cache():
    """Mock cache service."""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    cache.delete = Mock()
    return cache

@pytest.fixture
def mock_logger():
    """Mock logger service."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger
```

## Mocking External APIs

Use mocks to avoid real API calls:

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_github_api_call(mock_github_client):
    """Test GitHub API call with mocked client."""
    # Arrange
    mock_github_client.get_pull.return_value = Mock(number=123)

    # Act
    result = await repository.get_pr_diff()

    # Assert
    assert result is not None
    mock_github_client.get_pull.assert_called_once()
```

## Async Testing

Infrastructure components use async operations. Use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_method():
    """Test async method."""
    # Arrange
    component = AsyncComponent()

    # Act
    result = await component.async_method()

    # Assert
    assert result is not None
```

## Thread Safety Testing

Test thread-safe components:

```python
import threading

def test_thread_safety():
    """Test component is thread-safe."""
    component = ThreadSafeComponent()
    results = []
    errors = []

    def worker():
        try:
            results.append(component.method())
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = [threading.Thread(target=worker) for _ in range(10)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Assert no errors and consistent results
    assert len(errors) == 0
    assert len(results) == 10
```

## Coverage

Ensure good coverage for infrastructure:

```bash
# Run with coverage
pytest tests/unit/infrastructure/ --cov=ccpragents.infrastructure --cov-report=html
```

**Target Coverage:** >75% for infrastructure (external dependencies may reduce coverage)

## Related Documentation

- `../CLAUDE.md` - Unit test documentation
- `../../../ccpragents/infrastructure/CLAUDE.md` - Infrastructure documentation
- `../../../CLAUDE.md` - Project documentation
