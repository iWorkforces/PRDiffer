# AGENTS.md - Infrastructure Tests

Infrastructure layer testing: GitHub API, VCS providers, utilities, async execution, mocking.

## OVERVIEW
Tests for infrastructure components with external integrations, mocking, anyio async handling.

## STRUCTURE
```
tests/unit/infrastructure/
├── github/              # GitHub API tests (ApiClient, FileProcessor, DiffGenerator)
├── utils/               # Utility tests (RetryHandler, CircuitBreaker, CacheDecorator)
├── test_url_parser.py   # URL parsing and validation
├── test_settings_service.py
├── test_pr_diff_service.py
├── test_input_validator.py
├── test_gitlab_vcs_provider.py
├── test_diff_limits.py
├── test_console_logger.py
├── test_cache_service.py
├── test_async_parallel_executor.py
└── test_api_health_tracker.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add GitHub test** | `github/test_*.py` | Mock PyGithub responses |
| **Add VCS provider test** | `test_gitlab_vcs_provider.py` | Mock API responses |
| **Add utility test** | `utils/test_*.py` | Pure functions, edge cases |
| **Test DI service** | `test_*.py` | Inject dependencies, verify behavior |
| **Test async I/O** | `test_async_parallel_executor.py` | Use anyio (not asyncio) |

## CONVENTIONS

### Mocking External Services
```python
from unittest.mock import Mock, patch

def test_github_api_client():
    '''Mock PyGithub responses'''
    with patch('github.Github') as mock_github:
        mock_repo = Mock()
        mock_github.return_value.get_repo.return_value = mock_repo
        
        client = GitHubAPIClient()
        result = client.get_repository('owner/repo')
        
        assert result == mock_repo
```

### Async Testing (anyio-first)
```python
import anyio
import pytest

@pytest.mark.anyio
async def test_async_parallel_executor():
    '''Use anyio primitives (NOT asyncio)'''
    executor = AsyncParallelExecutor(max_workers=5)
    
    async def task():
        await anyio.sleep(0.1)
        return 'done'
    
    results = await executor.execute_parallel([task(), task()])
    assert len(results) == 2
```

### Thread Safety Testing
```python
import pytest
import anyio

@pytest.mark.thread_safety
@pytest.mark.anyio
async def test_cache_thread_safety(run_concurrently):
    '''Test thread-safe operations with anyio.Semaphore'''
    cache = CacheService()
    
    async def write_task(i):
        cache.set(f'key_{i}', f'value_{i}')
    
    # run_concurrently is a fixture that uses anyio.Semaphore
    await run_concurrently([write_task(i) for i in range(100)])
    
    assert len(cache._cache) == 100
```

### Manual Caching Pattern Tests (RLock)
```python
def test_get_settings_manual_caching():
    '''Test manual caching with RLock (no @lru_cache)'''
    from prdiffer.infrastructure.services.settings_service import get_settings
    
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Should return same instance (singleton)
    assert settings1 is settings2
```

### Retry Logic Tests
```python
@pytest.mark.anyio
async def test_retry_handler_exponential_backoff():
    '''Test exponential backoff with jitter'''
    handler = UnifiedRetryHandler(max_retries=3, base_delay=0.1)
    
    call_count = 0
    
    async def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception('Temporary failure')
        return 'success'
    
    result = await handler.retry_async(failing_func)
    
    assert result == 'success'
    assert call_count == 3
```

### Circuit Breaker Tests
```python
def test_circuit_breaker_state_transitions():
    '''Test CLOSED → OPEN → HALF_OPEN → CLOSED'''
    breaker = CircuitBreaker(failure_threshold=3, timeout=1)
    
    # Initial state: CLOSED
    assert breaker.state == CircuitBreakerState.CLOSED
    
    # Trigger 3 failures → OPEN
    for _ in range(3):
        breaker.record_failure()
    assert breaker.state == CircuitBreakerState.OPEN
    
    # Wait for timeout → HALF_OPEN
    time.sleep(1.1)
    assert breaker.can_attempt()
    assert breaker.state == CircuitBreakerState.HALF_OPEN
    
    # Success → CLOSED
    breaker.record_success()
    assert breaker.state == CircuitBreakerState.CLOSED
```

### Security Testing (Injection Detection)
```python
@pytest.mark.security
def test_command_injection_detection():
    '''Test pattern-based injection detection'''
    from prdiffer.infrastructure.security.injection_detector import InjectionDetector
    
    # Should detect command injection
    with pytest.raises(ValidationError, match='Command injection'):
        InjectionDetector.detect_all('$(rm -rf /)')
    
    with pytest.raises(ValidationError, match='Path traversal'):
        InjectionDetector.detect_all('../../../etc/passwd')
```

## ANTI-PATTERNS

- ❌ Integration tests in unit/ (use integration/ directory)
- ❌ Real API calls (mock all external dependencies)
- ❌ Using asyncio primitives (use anyio: Lock, Semaphore, create_task_group)
- ❌ Missing mocks for HTTP/IO operations
- ❌ Blocking I/O in async tests (use AsyncParallelExecutor)
- ❌ Using @pytest.mark.asyncio (use @pytest.mark.anyio)
- ❌ Testing with @lru_cache on settings (project uses manual caching)
