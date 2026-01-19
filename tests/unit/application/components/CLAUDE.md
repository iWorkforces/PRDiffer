# CLAUDE.md - Unit Tests: Application Components

This file provides guidance for working with unit tests for application components.

**Current Version:** 0.4.7

## Overview

Unit tests for application components verify the correctness of individual application-layer components in isolation.

## Test Files

Test files in this directory should test components from `prdiffer/application/components/`:

- `test_authentication.py` - Tests for `authentication.py`
- `test_rate_limiter.py` - Tests for `rate_limiter.py`
- `test_metrics_tracker.py` - Tests for `metrics_tracker.py`
- `test_health_monitor.py` - Tests for `health_monitor.py`
- `test_pr_operation_handler.py` - Tests for `pr_operation_handler.py`
- `test_server_configuration.py` - Tests for `server_configuration.py`

## Writing Tests

### Test Structure

```python
"""Unit tests for [component]."""

import pytest
from unittest.mock import Mock, patch
from prdiffer.application.components import [Component]

class Test[Component]:
    """Unit tests for [Component]."""

    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        # Setup component with mock dependencies
        deps = Mock()
        return [Component](deps)

    def test_[feature](self, component):
        """Test [feature] works correctly."""
        # Arrange
        # Set up test data

        # Act
        result = component.[method]()

        # Assert
        assert result == expected
```

### Best Practices

1. **Isolate Components**: Test each component independently
2. **Mock Dependencies**: Mock external dependencies (services, repositories)
3. **Test Public APIs**: Focus on public methods, not implementation details
4. **Use Fixtures**: Leverage pytest fixtures for common setup
5. **Clear Names**: Use descriptive test names that explain what is tested

## Running Tests

### Run All Component Tests
```bash
# Using pytest
pytest tests/unit/application/components/ -v

# Using unittest script
./start-unittest.sh --run tests/unit/application/components/
```

### Run Specific Test File
```bash
# Using pytest
pytest tests/unit/application/components/test_rate_limiter.py -v

# Using unittest script
./start-unittest.sh --file tests/unit/application/components/test_rate_limiter.py
```

### Run Specific Test
```bash
# Using pytest
pytest tests/unit/application/components/test_rate_limiter.py::test_rate_limiting -v
```

## Component-Specific Testing

### Authentication Component
Test API key authentication:
- Valid token acceptance
- Invalid token rejection
- Token format validation
- SHA-256 hashing
- Admin vs regular user keys

### Rate Limiter Component
Test rate limiting:
- Rate limit enforcement
- Per-client rate limiting
- Rate limit reset
- Concurrent requests
- Sliding window behavior

### Metrics Tracker Component
Test metrics collection:
- Request counting
- Error tracking
- Performance metrics
- Metric aggregation
- Statistics calculation

### Health Monitor Component
Test health monitoring:
- Health check status
- Component health
- Degraded state detection
- Recovery detection

### PR Operation Handler Component
Test PR operations:
- PR diff retrieval coordination
- Error handling
- Cache integration
- Retry logic

### Server Configuration Component
Test server configuration:
- Configuration loading
- Environment variable handling
- Default values
- Validation

## Mocking Dependencies

Application components depend on domain services. Mock these dependencies:

```python
from unittest.mock import Mock

@pytest.fixture
def mock_logger():
    """Mock logger service."""
    return Mock()

@pytest.fixture
def mock_settings():
    """Mock settings service."""
    settings = Mock()
    settings.get.return.value = "test_value"
    return settings

@pytest.fixture
def component(mock_logger, mock_settings):
    """Create component with mocked dependencies."""
    return RateLimiter(logger=mock_logger, settings=mock_settings)
```

## Test Fixtures

Create reusable fixtures in `conftest.py`:

```python
# tests/unit/application/components/conftest.py

import pytest
from unittest.mock import Mock

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
    return settings

@pytest.fixture
def mock_cache():
    """Mock cache service."""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    return cache
```

## Async Testing

Application components may have async methods. Use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_method(component):
    """Test async method works correctly."""
    result = await component.async_method()
    assert result is not None
```

## Coverage

Ensure high test coverage for application components:

```bash
# Run with coverage
pytest tests/unit/application/components/ --cov=prdiffer.application.components --cov-report=html
```

**Target Coverage:** >80% for application components

## Related Documentation

- `../CLAUDE.md` - Unit test documentation
- `../../../prdiffer/application/components/CLAUDE.md` - Component documentation
- `../../../CLAUDE.md` - Project documentation
