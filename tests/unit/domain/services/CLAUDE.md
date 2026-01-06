# CLAUDE.md - Unit Tests: Domain Services

This file provides guidance for working with unit tests for domain service interfaces.

## Overview

Unit tests for domain services verify the correctness of service interfaces and their implementations. Domain services define the contracts for external operations.

## Test Files

Test files in this directory should test services from `ccpragents/domain/services/`:

- `test_cache.py` - Tests for `CacheServiceInterface`
- `test_logger.py` - Tests for `LoggerServiceInterface`
- `test_settings.py` - Tests for `SettingsServiceInterface`
- `test_github_api.py` - Tests for `GitHubAPIServiceInterface`
- `test_diff.py` - Tests for `DiffServiceInterface`
- `test_pattern_matching.py` - Tests for `PatternMatchingServiceInterface`
- `test_retry.py` - Tests for `RetryServiceInterface`
- `test_pr_diff_service.py` - Tests for `PRDiffServiceInterface`
- `test_repository_cache.py` - Tests for `RepositoryCacheServiceInterface`

## Writing Tests

### Test Structure

```python
"""Unit tests for [service]."""

import pytest
from unittest.mock import Mock
from ccpragents.domain.services import [Service]Interface

class Test[Service]Interface:
    """Unit tests for [Service] interface."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        # Create implementation or mock
        return [Service]Implementation()

    def test_[method](self, service):
        """Test [method] works correctly."""
        # Arrange
        test_data = {...}

        # Act
        result = service.[method](test_data)

        # Assert
        assert result == expected
```

### Best Practices

1. **Test Interface Contracts**: Verify interface methods work as specified
2. **Test Implementations**: Test concrete implementations in infrastructure layer
3. **Mock Dependencies**: Mock external services (API calls, file I/O)
4. **Test Error Handling**: Verify proper error handling
5. **Test Edge Cases**: Boundary conditions, None values, empty data

## Running Tests

### Run All Service Tests
```bash
# Using pytest
pytest tests/unit/domain/services/ -v

# Using unittest script
./start-unittest.sh --run tests/unit/domain/services/
```

### Run Specific Test File
```bash
# Using pytest
pytest tests/unit/domain/services/test_cache.py -v

# Using unittest script
./start-unittest.sh --file tests/unit/domain/services/test_cache.py
```

## Service-Specific Testing

### Cache Service
Test caching operations:
- **Get**: Retrieve cached values
- **Set**: Store values in cache
- **Delete**: Remove cached values
- **Clear**: Clear all cache entries
- **Exists**: Check if key exists
- **Commit-based Invalidation**: Cache invalidation on commit changes

### Logger Service
Test logging operations:
- **Debug**: Debug level logging
- **Info**: Info level logging
- **Warning**: Warning level logging
- **Error**: Error level logging
- **Structured Logging**: Context-aware logging
- **Log Levels**: Respect log level settings

### Settings Service
Test configuration management:
- **Get**: Retrieve configuration values
- **Set**: Update configuration values
- **Default Values**: Return defaults when not set
- **Type Conversion**: Proper type conversion
- **Environment Overrides**: Environment variable priority

### GitHub API Service
Test GitHub API operations:
- **Get File**: Retrieve file content
- **Get PR**: Fetch pull request data
- **Get Commit**: Get commit information
- **List Files**: List PR files
- **Error Handling**: API errors, rate limits

### Diff Service
Test diff operations:
- **Generate Diff**: Create unified diff
- **Parse Diff**: Parse diff format
- **Apply Patch**: Apply patch to content
- **Extended Diff**: Create extended diff with context

### Pattern Matching Service
Test pattern matching:
- **Match Pattern**: Check if file matches pattern
- **Wildcard Support**: Support for * and ** wildcards
- **Extension Check**: Validate file extensions
- **Ignore Patterns**: Check ignore patterns

### Retry Service
Test retry logic:
- **Retry on Failure**: Retry failed operations
- **Exponential Backoff**: Increasing delay between retries
- **Max Retries**: Respect retry limit
- **Permanent Failures**: Don't retry permanent errors

### PR Diff Service
Test PR diff operations:
- **Get PR Diff**: Retrieve PR diff data
- **Cache Integration**: Use cache for performance
- **Commit Tracking**: Track latest commit SHA
- **Error Handling**: Graceful error handling

### Repository Cache Service
Test repository caching:
- **Get Repository**: Get cached repository instance
- **Set Repository**: Cache repository instance
- **Invalidate**: Invalidate cached repository
- **Key Generation**: Generate cache keys

## Test Fixtures

Create reusable fixtures in `conftest.py`:

```python
# tests/unit/domain/services/conftest.py

import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_cache():
    """Mock cache service."""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    cache.delete = Mock()
    cache.exists = Mock(return_value=False)
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

@pytest.fixture
def mock_settings():
    """Mock settings service."""
    settings = Mock()
    settings.get = Mock(return_value="default")
    return cache
```

## Async Testing

Domain service interfaces may have async methods. Use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_method(service):
    """Test async method works correctly."""
    result = await service.async_method()
    assert result is not None
```

## Mocking External Dependencies

Domain services often interact with external systems. Mock these:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_github_api_call():
    """Test GitHub API call with mocked response."""
    # Arrange
    mock_response = Mock()
    mock_response.json = AsyncMock(return_value={"data": "test"})

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        # Act
        result = await github_service.get_data()

        # Assert
        assert result == {"data": "test"}
```

## Coverage

Ensure good coverage for domain services:

```bash
# Run with coverage
pytest tests/unit/domain/services/ --cov=ccpragents.domain.services --cov-report=html
```

**Target Coverage:** >80% for domain services

## Related Documentation

- `../CLAUDE.md` - Unit test documentation
- `../../../ccpragents/domain/services/CLAUDE.md` - Service documentation
- `../../../CLAUDE.md` - Project documentation
