# CLAUDE.md - Unit Tests

This file provides guidance for working with unit tests in PRDiffer.

**Current Version:** 0.4.8

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

For async components, PRDiffer uses `pytest-asyncio` and `anyio` for comprehensive async testing support.

### Pytest-Asyncio Configuration

The project uses `pytest-asyncio` with auto mode configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Basic Async Test Structure

```python
import pytest
import anyio

@pytest.mark.asyncio
async def test_async_method():
    """Test async method works correctly."""
    component = AsyncComponent()
    result = await component.async_method()
    assert result is not None
```

### Testing with Anyio Task Groups

When testing parallel execution with anyio task groups:

```python
import anyio
import pytest

@pytest.mark.asyncio
async def test_parallel_processing():
    """Test parallel processing with task groups."""
    results = []

    async def process_item(item):
        # Simulate async processing
        await anyio.sleep(0.01)
        results.append(item * 2)

    async with anyio.create_task_group() as tg:
        for i in range(5):
            tg.start_soon(process_item, i)

    # All tasks complete before assertion
    assert len(results) == 5
    assert sorted(results) == [0, 2, 4, 6, 8]
```

### Testing Error Handling Strategies

For components with multiple error handling strategies (IGNORE, RAISE, COLLECT, CONTINUE):

```python
@pytest.mark.asyncio
async def test_error_strategy_ignore():
    """Test IGNORE error strategy (default)."""
    executor = AsyncParallelExecutor(error_strategy="ignore")

    async def failing_task(item):
        if item == 2:
            raise ValueError("Failed")
        return item * 2

    results = await executor.execute_batch(failing_task, [1, 2, 3, 4])

    # Error logged, only successful results returned
    assert results == [2, 6, 8]

@pytest.mark.asyncio
async def test_error_strategy_raise():
    """Test RAISE error strategy."""
    executor = AsyncParallelExecutor(error_strategy="raise")

    async def failing_task(item):
        if item == 2:
            raise ValueError("Failed")
        return item * 2

    with pytest.raises(ValueError):
        await executor.execute_batch(failing_task, [1, 2, 3])
```

### Mocking Anyio Primitives

When testing components that use anyio primitives, you can mock them:

```python
from unittest.mock import AsyncMock, patch, Mock

@pytest.mark.asyncio
async def test_with_mocked_semaphore():
    """Test component with mocked semaphore."""
    with patch('anyio.Semaphore') as mock_semaphore_cls:
        # Create mock semaphore instance
        mock_semaphore = AsyncMock()
        mock_semaphore.__aenter__ = AsyncMock(return_value=mock_semaphore)
        mock_semaphore.__aexit__ = AsyncMock()

        # Set mock semaphore class to return mock instance
        mock_semaphore_cls.return_value = mock_semaphore

        # Test component that uses semaphore
        executor = AsyncParallelExecutor(max_concurrent=5)
        # ... test logic ...

        # Verify semaphore was created with correct value
        mock_semaphore_cls.assert_called_with(5)

@pytest.mark.asyncio
async def test_with_mocked_lock():
    """Test component with mocked lock."""
    with patch('anyio.Lock') as mock_lock_cls:
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()

        mock_lock_cls.return_value = mock_lock

        # Test component that uses lock
        service = RequestCoalescingService()
        result = await service.coalesce("key", lambda: "value", 10.0)

        # Verify lock was used
        mock_lock.acquire.assert_called()
```

### Testing Timeout and Cancellation

For timeout and cancellation testing:

```python
import anyio
import pytest

@pytest.mark.asyncio
async def test_timeout_protection():
    """Test timeout protection."""
    async def slow_operation():
        await anyio.sleep(5)
        return "done"

    # Should timeout after 0.1 seconds
    with anyio.move_on_after(0.1) as scope:
        await slow_operation()

    # Verify timeout was triggered
    assert scope.cancel_called is True

@pytest.mark.asyncio
async def test_cancellation():
    """Test task cancellation."""
    task_started = False
    task_cancelled = False

    async def cancellable_task(*, task_status):
        nonlocal task_started, task_cancelled
        task_started = True
        try:
            await anyio.sleep_forever()
        except anyio.get_cancelled_exc_class():
            task_cancelled = True
            raise

    async with anyio.create_task_group() as tg:
        tg.start_soon(cancellable_task)
        await anyio.sleep(0.01)  # Let task start
        tg.cancel_scope.cancel()

    assert task_started is True
    assert task_cancelled is True
```

### Deterministic Testing with Time Control

When testing time-based logic:

```python
import anyio
import pytest

@pytest.mark.asyncio
async def test_race_condition_deterministic():
    """Test for race conditions with controlled execution."""
    results = []
    execution_order = []

    async def task_a():
        execution_order.append("a_start")
        await anyio.sleep(0)
        results.append("a")
        execution_order.append("a_end")

    async def task_b():
        execution_order.append("b_start")
        await anyio.sleep(0)
        results.append("b")
        execution_order.append("b_end")

    async with anyio.create_task_group() as tg:
        tg.start_soon(task_a)
        tg.start_soon(task_b)

    # Both tasks should complete
    assert set(results) == {"a", "b"}
    # Verify execution order (deterministic with anyio)
    assert execution_order[0] in ["a_start", "b_start"]
```

### Async Fixtures

Create async fixtures for reusable async test setup:

```python
# tests/unit/conftest.py

import pytest
import anyio
from unittest.mock import Mock

@pytest.fixture
async def async_cache_service():
    """Async fixture for cache service."""
    from prdiffer.infrastructure import get_cache_service
    cache = get_cache_service()
    cache.clear()  # Clean state for each test
    yield cache
    cache.clear()  # Cleanup after test

@pytest.fixture
async def async_executor():
    """Async fixture for parallel executor."""
    from prdiffer.infrastructure import get_async_parallel_executor
    executor = get_async_parallel_executor(max_concurrent=5, timeout=30.0)
    yield executor

@pytest.fixture
def mock_anyio_lock():
    """Mock anyio.Lock for testing."""
    with patch('anyio.Lock') as mock_lock_cls:
        mock_lock = AsyncMock()
        mock_lock.__aenter__ = AsyncMock(return_value=mock_lock)
        mock_lock.__aexit__ = AsyncMock()
        mock_lock_cls.return_value = mock_lock
        yield mock_lock
```

### Testing Request Coalescing

For request coalescing service testing:

```python
import anyio
import pytest

@pytest.mark.asyncio
async def test_request_coalescing_deduplication():
    """Test that concurrent requests are coalesced."""
    coalescer = get_request_coalescing_service()
    fetch_count = 0

    async def fetch_func():
        nonlocal fetch_count
        fetch_count += 1
        await anyio.sleep(0.1)
        return "result"

    async def make_request():
        return await coalescer.coalesce("test_key", fetch_func, 30.0)

    # Make concurrent requests
    async with anyio.create_task_group() as tg:
        for _ in range(10):
            tg.start_soon(make_request)

    # Should only fetch once due to coalescing
    assert fetch_count == 1

@pytest.mark.asyncio
async def test_request_coalescing_timeout():
    """Test timeout protection in coalescing."""
    coalescer = get_request_coalescing_service()

    async def slow_fetch():
        await anyio.sleep(10)
        return "result"

    # Should timeout after 0.1 seconds
    with pytest.raises(TimeoutError):
        await coalescer.coalesce("key", slow_fetch, 0.1)
```

### Test Isolation Patterns

Ensure async tests don't interfere with each other:

```python
import pytest

@pytest.mark.asyncio
async def test_isolated_cache_operations():
    """Test that cache operations are isolated."""
    cache = get_cache_service()

    # Use unique key to avoid conflicts
    import uuid
    unique_key = f"test_{uuid.uuid4()}"

    cache.set(unique_key, "commit123", {"data": "value"})
    result = cache.get(unique_key, "commit123")

    assert result == {"data": "value"}

    # Cleanup
    cache.invalidate(unique_key)
```

### Common Async Testing Pitfalls

**Pitfall 1: Missing @pytest.mark.asyncio**
```python
# BAD - Will fail: RuntimeError: Event loop is closed
def test_async_without_decorator():
    result = await async_function()

# GOOD - Properly decorated
@pytest.mark.asyncio
async def test_async_with_decorator():
    result = await async_function()
```

**Pitfall 2: Not awaiting coroutines**
```python
# BAD - Returns coroutine object, not result
def test_not_awaited():
    result = async_function()  # Missing await
    assert result == "expected"

# GOOD - Awaiting coroutine
@pytest.mark.asyncio
async def test_properly_awaited():
    result = await async_function()
    assert result == "expected"
```

**Pitfall 3: Mixing sync and async incorrectly**
```python
# BAD - Using asyncio.run() in async test
@pytest.mark.asyncio
async def test_blocking_asyncio_run():
    result = asyncio.run(other_async_function())  # Blocking!

# GOOD - Just await the coroutine
@pytest.mark.asyncio
async def test_proper_await():
    result = await other_async_function()  # Correct
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
