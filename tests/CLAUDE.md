# CLAUDE.md - Tests Directory

This file provides guidance for working with the test suite in PRDiffer.

**Current Version:** 0.4.7

## OverviewPRDiffer

The `tests/` directory contains the complete test suite for the CCPRAgents project, including unit tests, integration tests, and test utilities. Tests are organized to mirror the main package structure and follow pytest conventions.

## Directory Structure

```
tests/
├── __init__.py                      # Test package initialization
├── CLAUDE.md                        # This file
├── unit/                            # Unit tests
│   ├── __init__.py
│   └── infrastructure/              # Infrastructure layer tests
│       ├── __init__.py
│       └── test_input_validator.py  # Security validation tests
├── integration/                     # Integration tests
│   ├── __init__.py
│   └── mcp_server_manual_test.py   # Manual MCP server testing
├── test_cache_hashing.py           # Cache key hashing tests
├── test_github_client.py           # GitHub client tests
└── test_parallel_diff.py           # Parallel diff processing tests
```

## Test Configuration

### Pytest Settings (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests (isolated, fast) |
| `@pytest.mark.integration` | Integration tests (may use external services) |
| `@pytest.mark.slow` | Slow-running tests |

## Running Tests

### Basic Commands

```bash
# Run all tests
./start-unittest.sh --run

# Run with coverage
./start-unittest.sh --coverage

# Run in parallel (faster)
./start-unittest.sh --parallel

# Run specific test file
./start-unittest.sh --file tests/test_cache_hashing.py

# Run tests matching pattern
./start-unittest.sh --pattern validator

# Watch mode (re-run on changes)
./start-unittest.sh --watch
```

### Direct pytest Usage

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific marker
uv run pytest -m unit
uv run pytest -m integration

# Run with coverage report
uv run pytest --cov=prdiffer

# Run specific test class
uv run pytest tests/unit/infrastructure/test_input_validator.py::TestGitHubURLValidation
```

## Test Patterns

### Unit Test Structure

Unit tests follow a consistent pattern:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestComponentName:
    """Test description for the component."""

    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Arrange
        input_value = "test_input"

        # Act
        result = component.process(input_value)

        # Assert
        assert result == expected_value

    @pytest.mark.parametrize("input,expected", [
        ("valid", True),
        ("invalid", False),
    ])
    def test_parameterized_behavior(self, input, expected):
        """Test behavior with multiple inputs."""
        assert component.validate(input) == expected
```

### Async Test Structure

Async tests use `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation."""
    result = await async_component.process()
    assert result is not None
```

### Fixture Patterns

Common fixture patterns used:

```python
@pytest.fixture
def mock_settings():
    """Mock settings service."""
    mock = Mock()
    mock.get.side_effect = lambda key, default: {
        "key1": "value1",
        "key2": "value2",
    }.get(key, default)
    return mock

@pytest.fixture
def sample_pr_diff():
    """Create sample PRDiff for testing."""
    return PRDiff(
        diff_content="sample diff",
        commit_messages="1. Initial commit",
    )
```

## Coverage Configuration

### Settings (`pyproject.toml`)

```toml
[tool.coverage.run]
source = ["prdiffer"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
precision = 2
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

### Coverage Commands

```bash
# Generate coverage report
./start-unittest.sh --coverage

# HTML coverage report
uv run pytest --cov=prdiffer --cov-report=html
```

## Key Test Files

### Security Tests (`test_input_validator.py`)

Comprehensive tests for input validation (ENHANCED in Sprint 1):
- URL validation (GitHub PR URLs)
- Repository identifier validation
- String sanitization
- Command injection detection
- SQL injection detection
- Path traversal prevention
- **Branch/ref validation** (NEW in Sprint 1)

**Security Test Patterns** (NEW in Sprint 1):
```python
# Test command injection detection
def test_command_injection_rejected():
    with pytest.raises(SuspiciousOperationError):
        validate_github_url("https://github.com/owner/repo/pull/123; rm -rf /")

# Test SQL injection detection
def test_sql_injection_rejected():
    with pytest.raises(SuspiciousOperationError):
        sanitize_string("'; DROP TABLE users; --")

# Test branch validation
def test_branch_name_validation():
    # Valid branch names
    assert validate_branch_name("feature/new-functionality") == "feature/new-functionality"
    assert validate_branch_name("bugfix/issue-123") == "bugfix/issue-123"

    # Invalid branch names
    with pytest.raises(InputSanitizationError):
        validate_branch_name("../../etc/passwd")  # Path traversal
    with pytest.raises(InputSanitizationError):
        validate_branch_name("feature; rm -rf /")  # Command injection
```

### Thread Safety Tests (NEW in Sprint 2)

**Thread Safety Testing Patterns:**
```python
import pytest
import threading
import time

@pytest.mark.unit
class TestThreadSafety:
    """Test thread safety of concurrent operations."""

    def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe."""
        cache = get_cache_service()
        results = []
        exceptions = []

        def concurrent_get_set(key, value):
            try:
                cache.set(key, value, "commit123")
                result = cache.get(key)
                results.append(result)
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads
        threads = [
            threading.Thread(target=concurrent_get_set, args=(f"key{i}", f"value{i}"))
            for i in range(100)
        ]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify no exceptions and correct results
        assert len(exceptions) == 0
        assert len(results) == 100

    def test_request_coalescing_thread_safety(self):
        """Test that request coalescing is thread-safe."""
        coalescer = get_request_coalescing_service()
        call_count = [0]

        async def fetch_func():
            call_count[0] += 1
            await anyio.sleep(0.1)
            return "result"

        async def concurrent_requests():
            async with anyio.create_task_group() as tg:
                for i in range(10):
                    tg.start_soon(coalescer.coalesce, "test_key", fetch_func, 30.0)

        # Run concurrent requests
        anyio.run(concurrent_requests)

        # Should only call fetch_func once due to coalescing
        assert call_count[0] == 1

    def test_double_check_locking_pattern(self):
        """Test double-check locking pattern for performance and safety."""
        processor = get_file_processor(...)

        # First call - should initialize cache
        files1 = processor.get_pr_files(mock_pr)

        # Second call - should return cached value without lock
        files2 = processor.get_pr_files(mock_pr)

        # Verify cache was used (same object reference)
        assert files1 is files2
```

### Cache Tests (`test_cache_hashing.py`)

Tests for cache key hashing:
- MD5 hashing functionality
- Reverse mapping
- Configuration options
- Cache operations with hashed keys

### GitHub Client Tests (`test_github_client.py`)

Tests for GitHub API integration:
- Repository access
- PR diff retrieval
- Error handling

## Development Guidelines

### Adding New Tests

1. Create test file matching `test_*.py` pattern
2. Add appropriate markers (`@pytest.mark.unit`)
3. Use descriptive test names (`test_validates_github_url_format`)
4. Include docstrings explaining test purpose
5. Follow Arrange-Act-Assert pattern

### Mocking Best Practices

- Use `unittest.mock.Mock` for simple mocks
- Use `pytest.fixture` for reusable test data
- Mock at the boundary (external services, I/O)
- Avoid mocking internal implementation details

### Test Organization

- Mirror source code structure in test directories
- Group related tests in classes
- Use parametrize for testing multiple inputs
- Keep tests focused and independent

## Integration Testing

### Manual MCP Server Testing

```python
# tests/integration/mcp_server_manual_test.py
# Used for manual testing of MCP server functionality
```

### Integration Test Setup

Integration tests may require:
- Environment variables (`GITHUB_TOKEN`)
- Running MCP server
- Network access

## Troubleshooting

### Common Issues

**Async test errors:**
- Ensure `asyncio_mode = "auto"` in pytest config
- Use `@pytest.mark.asyncio` decorator

**Import errors:**
- Run tests from project root
- Ensure `uv install --dev` completed

**Mock not working:**
- Check mock target path matches import path
- Use `patch` with correct module path

### Debug Commands

```bash
# Run with debug output
uv run pytest -vvs

# Run single test with output
uv run pytest -vvs tests/test_cache_hashing.py::test_specific_function

# Show local variables on failure
uv run pytest --tb=long
```
