# AGENTS.md - Infrastructure Tests

Infrastructure layer testing: GitHub API, VCS providers, utilities, I/O handling.

## OVERVIEW
Tests for infrastructure components with external integrations, mocking, async handling.

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
| Task | Location |
|------|----------|
| **Add GitHub test** | `github/test_*.py` | Mock PyGithub responses |
| **Add VCS provider test** | `test_gitlab_vcs_provider.py` | Mock API responses |
| **Add utility test** | `utils/test_*.py` | Pure functions, edge cases |
| **Test DI service** | `test_*.py` | Inject dependencies, verify behavior |
| **Test async I/O** | `test_async_parallel_executor.py` | Use asyncio, verify concurrency |

## CONVENTIONS

### Mocking External Services
- **PyGithub**: Mock GitHub API responses via responses library
- **HTTP clients**: Mock httpx.AsyncClient responses
- **VCS providers**: Mock provider API responses

### Async Testing
- **pytest.mark.asyncio** for async tests
- **AsyncParallelExecutor tests**: Verify concurrency limits, task groups
- **anyio task groups**: Test structured concurrency

### I/O Testing
- **Cache service**: Mock storage layer, verify MD5 keys, TTL
- **Console logger**: Mock output capture, verify formatting
- **Settings service**: Mock file reading, config parsing

### Error Handling
- **RetryHandler**: Test exponential backoff, max retries
- **CircuitBreaker**: Test failure thresholds, state transitions
- **InputValidator**: Test injection detection, sanitization

## ANTI-PATTERNS

- **NO integration tests** → Use mocks, separate integration/ directory
- **NO real API calls** → Mock all external dependencies
- **NO blocking I/O tests** → Use AsyncParallelExecutor patterns
- **NO missing mocks** → Always mock HTTP/IO operations
