# CLAUDE.md - Unit Tests

This file provides guidance for working with unit tests in PRDiffer.

**Current Version:** 0.4.6

## Overview

Unit tests verify the correctness of individual components in isolation. Each test focuses on a single unit of code (function, class, method) without external dependencies.

## Directory Structure

```
tests/unit/
├── CLAUDE.md                   # This file
├── __init__.py                # Test package initialization
├── conftest.py                # Shared pytest fixtures
├── application/               # Application layer tests
│   ├── CLAUDE.md             # Application component tests guide
│   └── components/           # Application component tests
│       ├── test_authentication.py
│       ├── test_rate_limiter.py
│       ├── test_metrics_tracker.py
│       ├── test_health_monitor.py
│       ├── test_pr_operation_handler.py
│       └── test_server_configuration.py
├── domain/                    # Domain layer tests
│   ├── CLAUDE.md             # Domain tests guide
│   ├── entities/             # Domain entity tests
│   │   ├── test_file_patch.py
│   │   ├── test_pr_diff.py
│   │   └── test_edit_type.py
│   ├── repositories/         # Repository interface tests
│   ├── usecases/             # Use case tests
│   ├── services/             # Service interface tests
│   │   ├── CLAUDE.md
│   │   ├── test_cache.py
│   │   ├── test_logger.py
│   │   ├── test_settings.py
│   │   └── ...
│   └── factories/            # Factory interface tests
└── infrastructure/            # Infrastructure layer tests
    ├── CLAUDE.md             # Infrastructure tests guide
    ├── test_github_repository.py
    ├── test_settings.py
    ├── test_cache_service.py
    ├── test_request_coalescing.py
    ├── test_async_parallel_executor.py
    ├── github/               # GitHub component tests
    ├── utils/                # Utility tests
    ├── logging/              # Logging tests
    └── security/             # Security tests
```

## Running Unit Tests

### Run All Unit Tests
```bash
# Using pytest
pytest tests/unit/ -v

# Using unittest script
./start-unittest.sh --run

# Run in parallel (faster)
./start-unittest.sh --parallel
```

### Run Specific Test Directory
```bash
# Application layer tests
pytest tests/unit/application/ -v

# Domain layer tests
pytest tests/unit/domain/ -v

# Infrastructure layer tests
pytest tests/unit/infrastructure/ -v
```

### Run Specific Test File
```bash
# Using pytest
pytest tests/unit/domain/entities/test_file_patch.py -v

# Using unittest script
./start-unittest.sh --file tests/unit/domain/entities/test_file_patch.py
```

### Run Tests Matching Pattern
```bash
# Using pytest
pytest tests/unit/ -k "test_cache" -v

# Using unittest script
./start-unittest.sh --pattern cache
```

### Run with Coverage
```bash
# Using pytest
pytest tests/unit/ --cov=prdiffer --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Organization

### By Layer
Tests are organized by architectural layer:
- **Application**: Tests for application components
- **Domain**: Tests for domain entities, use cases, service interfaces
- **Infrastructure**: Tests for infrastructure implementations

### By Component
Each component has its own test file:
- `test_[component_name].py` - Tests for `[component_name]`
- One test class per component: `Test[ComponentName]`

## Writing Unit Tests

### Basic Test Structure

```python
"""Unit tests for [component]."""

import pytest
from unittest.mock import Mock
from prdiffer.[layer] import [Component]

class Test[Component]:
    """Unit tests for [Component]."""

    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return [Component]()

    def test_[feature](self, component):
        """Test [feature] works correctly."""
        # Arrange
        test_input = ...

        # Act
        result = component.[method](test_input)

        # Assert
        assert result == expected
```

### Test Naming Conventions

- **File**: `test_[component_name].py`
- **Class**: `Test[ComponentName]`
- **Method**: `test_[feature]` or `test_[feature]_when_[condition]`

### Test Fixtures

Create shared fixtures in `conftest.py`:

```python
# tests/unit/conftest.py

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

## Test Principles

### Isolation
- Each test should be independent
- Tests should not depend on each other
- Mock external dependencies

### Fast
- Unit tests should run quickly
- Avoid real network calls
- Avoid file I/O operations

### Deterministic
- Tests should always produce same result
- No random data or time-based logic
- Consistent assertions

### Clear
- Descriptive test names
- Clear arrange-act-assert structure
- Helpful failure messages

## Async Testing

For async components, use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_method():
    """Test async method works correctly."""
    component = AsyncComponent()
    result = await component.async_method()
    assert result is not None
```

## Mocking

### Mock External Dependencies

```python
from unittest.mock import patch, Mock

def test_with_mock():
    """Test with mocked dependency."""
    # Arrange
    mock_dependency = Mock()
    mock_dependency.method.return_value = "test"

    # Act
    result = component.method(mock_dependency)

    # Assert
    assert result == "test"
    mock_dependency.method.assert_called_once()
```

### Patch External Modules

```python
def test_with_patch():
    """Test with patched module."""
    with patch('prdiffer.infrastructure.github.api') as mock_api:
        mock_api.get.return_value = Mock(data="test")
        result = component.fetch_data()
        assert result == "test"
```

## Parameterized Tests

Use `@pytest.mark.parametrize` for multiple test cases:

```python
@pytest.mark.parametrize("input,expected", [
    ("test.py", True),
    ("test.txt", False),
    ("test.md", True),
])
def test_file_validation(input, expected, component):
    """Test file validation with multiple cases."""
    result = component.validate_file(input)
    assert result == expected
```

## Exception Testing

Test that exceptions are raised correctly:

```python
import pytest

def test_invalid_input_raises_error():
    """Test invalid input raises appropriate error."""
    with pytest.raises(ValueError, match="Invalid input"):
        component.process("invalid")
```

## Test Coverage

### Run Coverage Analysis
```bash
# Generate coverage report
pytest tests/unit/ --cov=prdiffer --cov-report=html

# Generate terminal report
pytest tests/unit/ --cov=prdiffer --cov-report=term-missing
```

### Coverage Goals
- **Overall**: >80% coverage
- **Domain**: >90% coverage (critical business logic)
- **Infrastructure**: >75% coverage (external dependencies)

## Continuous Integration

Unit tests run in CI/CD pipeline:
- On every pull request
- Before merging to main
- On scheduled builds

## Debugging Tests

### Verbose Output
```bash
pytest tests/unit/ -vv -s
```

### Stop on First Failure
```bash
pytest tests/unit/ -x
```

### Run with Debugger
```bash
pytest tests/unit/ --pdb
```

### Run Specific Test
```bash
pytest tests/unit/domain/entities/test_file_patch.py::TestFilePatchInfo::test_creation
```

## Best Practices

1. **One Assertion Per Test**: Keep tests focused
2. **Use Descriptive Names**: Explain what is being tested
3. **Arrange-Act-Assert**: Clear test structure
4. **Mock External Dependencies**: Avoid real API calls
5. **Test Edge Cases**: Include boundary conditions
6. **Keep Tests Fast**: Unit tests should run in seconds
7. **Independent Tests**: No dependencies between tests
8. **Clean Up**: Use fixtures for setup/teardown

## Common Pitfalls

### Testing Implementation Details
```python
# BAD - Tests private method
def test_private_method(component):
    component._private_method()

# GOOD - Tests public behavior
def test_public_behavior(component):
    result = component.public_method()
    assert result == expected
```

### Brittle Tests
```python
# BAD - Hardcoded values
assert response == {"key": "value"}

# GOOD - Semantic assertions
assert response["success"] is True
```

### Missing Assertions
```python
# BAD - No assertion
component.method()

# GOOD - Has assertion
result = component.method()
assert result is not None
```

## Related Documentation

- `../CLAUDE.md` - Test documentation
- `integration/CLAUDE.md` - Integration test documentation
- `../../prdiffer/CLAUDE.md` - Package structure
