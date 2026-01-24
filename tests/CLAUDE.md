# CLAUDE.md - Tests Directory

This file provides guidance for working with the test suite in PRDiffer.

**Current Version:** 0.4.8

## Overview

The `tests/` directory contains the complete test suite for the PRDifferMCP project, including **50+ test files** organized across unit, integration, and performance layers. Tests mirror the Clean Architecture structure and follow pytest conventions with comprehensive security, thread safety, and async testing.

## Test Organization

```
tests/
├── unit/                                    # Unit Tests
│   ├── application/                         # Application Layer Tests
│   │   ├── components/                      # Component tests
│   │   │   ├── test_authentication.py       # Authentication (API keys, SHA-256, JWT)
│   │   │   ├── test_health_monitor.py       # Health monitoring tests
│   │   │   ├── test_metrics_tracker.py      # Metrics tracking tests
│   │   │   └── test_rate_limiter.py         # Rate limiting tests
│   │   └── test_mcp_server_health_status.py # MCP server health tests
│   ├── domain/                              # Domain Layer Tests
│   │   ├── entities/                        # Entity tests
│   │   │   ├── test_file_patch_info.py      # FilePatchInfo entity
│   │   │   └── test_pr_diff.py              # PRDiff entity
│   │   ├── services/                        # Service interface tests
│   │   │   └── test_service_interfaces.py   # Service interface tests
│   │   └── usecases/                        # Use case tests
│   │       └── test_pr_diff_usecases.py     # GetPRDiffUseCase tests
│   └── infrastructure/                      # Infrastructure Layer Tests
│       ├── github/                          # GitHub component tests
│       │   ├── test_api_client.py           # GitHub API client
│       │   ├── test_diff_generator.py       # Diff generator
│       │   └── test_file_processor.py       # File processor
│       ├── utils/                           # Utility tests
│       │   └── test_cache_decorator.py      # Cache decorator (skipped)
│       ├── test_api_client.py               # GitHub API client tests
│       ├── test_api_health_tracker.py       # API health monitoring
│       ├── test_async_parallel_executor.py  # Async parallel execution (743 lines)
│       ├── test_cache_service.py            # Cache service (492 lines)
│       ├── test_circuit_breaker.py         # Circuit breaker (678 lines)
│       ├── test_console_logger.py           # Console logger
│       ├── test_diff_limits.py              # Diff limits testing
│       ├── test_input_validator.py          # Security validation (571 lines)
│       ├── test_pr_diff_service.py          # PR diff service
│       ├── test_rate_limiter.py             # Rate limiter tests
│       ├── test_retry_handler.py            # Retry logic (242 lines)
│       ├── test_settings_service.py         # Settings service
│       └── [additional infrastructure tests]
├── integration/                             # Integration Tests
│   ├── test_complete_workflow.py            # End-to-end workflow tests
│   ├── test_error_scenarios.py              # Error handling tests
│   ├── test_real_github_api.py              # Real GitHub API integration
│   ├── test_security.py                     # Security validation tests
│   └── mcp_server_manual_test.py            # Manual testing utility
├── performance/                             # Performance Tests
│   └── test_performance.py                  # Performance benchmarks (375 lines)
├── conftest.py                              # Main pytest fixtures (497 lines)
├── test_cache_hashing.py                    # Cache hashing tests
├── test_github_client.py                    # GitHub client tests
├── test_phase1_improvements.py              # Phase 1 critical fixes (707 lines)
├── test_phase2_improvements.py              # Phase 2 diff optimization (724 lines)
├── test_phase3_improvements.py              # Phase 3 API enhancement (587 lines)
├── test_phase4_improvements.py              # Phase 4 architecture refinement (698 lines)
└── test_version_consistency.py              # Version consistency tests
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
| `@pytest.mark.unit` | Unit tests (isolated, fast, no external dependencies) |
| `@pytest.mark.integration` | Integration tests (may use external services) |
| `@pytest.mark.slow` | Slow-running tests |
| `@pytest.mark.security` | Security and vulnerability tests |
| `@pytest.mark.thread_safety` | Thread safety and concurrency tests |

## Phase-Based Test Organization

The test suite is organized into **4 improvement phases** for tracking development progress:

### Phase 1: Critical Fixes
Tests for critical infrastructure improvements:
- LRU cache fixes
- TTL (time-to-live) implementation
- Retry handler improvements
- Circuit breaker pattern
- ReDoS (regular expression denial of service) fixes
- Test file: `test_phase1_improvements.py` (707 lines)

### Phase 2: Diff Builder Optimization
Tests for diff generation performance improvements:
- Binary file handling
- Chunked processing for large files
- Streaming diff generation
- Parallel file content fetching
- Test file: `test_phase2_improvements.py` (724 lines)

### Phase 3: API Enhancement
Tests for API and data model improvements:
- Extended FilePatchInfo with metadata
- Enhanced PRDiff with structured data
- Structured error codes implementation
- Test file: `test_phase3_improvements.py` (587 lines)

### Phase 4: Architecture Refinement
Tests for architectural improvements:
- GitHubConfig dataclass implementation
- AsyncParallelExecutor with anyio
- GlobalCircuitBreakerRegistry
- Test file: `test_phase4_improvements.py` (698 lines)

## Comprehensive Test Features

### Security Testing (571 lines)
**File**: `test_input_validator.py`

Comprehensive security validation tests:
- SQL injection prevention patterns
- Command injection prevention (shell metacharacters, command substitution)
- Path traversal prevention (parent directory, system directories)
- XSS attack prevention
- GitHub URL validation with strict patterns
- Repository identifier validation (owner/repo naming rules)
- Token format validation
- User ID validation
- Safe logging sanitization

### Thread Safety Testing
Multiple thread safety test scenarios:
- **Concurrent Cache Operations**: 100 threads testing cache get/set operations
- **Circuit Breaker**: Concurrent failures/successes with 5 threads
- **Request Coalescing**: Thread-safe deduplication with anyio primitives
- **Double-Check Locking**: Pattern verification for performance and safety

### Async Testing with anyio
Full async/await support with anyio primitives:
- pytest-asyncio compatibility
- Anyio task group testing
- Timeout handling tests (`anyio.fail_after()`)
- Task cancellation tests
- Semaphore and Lock mocking

### Performance Testing
**File**: `tests/performance/test_performance.py` (375 lines)

Performance benchmarks:
- URL validation throughput (10k URLs/sec target)
- API key hashing performance
- Authentication performance
- Pattern matching performance
- Memory efficiency tests (bounded deque usage)
- Request coalescing efficiency

## Coverage Goals

| Layer | Target Coverage |
|-------|----------------|
| Overall | >80% |
| Domain | >90% (critical business logic) |
| Infrastructure | >75% (external dependencies) |
| Application | >85% (application orchestration) |

## Test Statistics

**Total Test Files**: 50+
**Total Lines of Test Code**: ~15,000+
**Test Organization**: Mirrors Clean Architecture structure
**Key Test Files**:
- Most comprehensive: `test_input_validator.py` (571 lines)
- Most complex: `test_async_parallel_executor.py` (743 lines)
- Most coverage: `test_phase2_improvements.py` (724 lines)

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
