# AGENTS.md - Application Layer Unit Tests

Unit tests for MCP server, components, factories, and utilities. 14 files, ~6000 lines.

## OVERVIEW
Tests application layer orchestration: authentication, rate limiting, metrics, health, PR operations, tool registry.

## STRUCTURE
```
tests/unit/application/
├── components/               # Component tests (6 files)
│   ├── test_authentication.py      # 1145 lines, API key hashing, env config
│   ├── test_rate_limiter.py        # 521 lines, sliding window, concurrency
│   ├── test_metrics_tracker.py     # 564 lines, request tracking, timing
│   ├── test_health_monitor.py      # 408 lines, health checks
│   ├── test_pr_operation_handler.py # 486 lines, PR diff operations
│   └── test_server_configuration.py # 458 lines, server config
├── factories/                # Factory tests (1 file)
│   └── test_application_factory.py  # 152 lines, singleton, component creation
├── utils/                    # Utility tests (1 file)
│   └── test_pr_url_parser.py        # 228 lines, URL parsing, validation
├── test_tool_registry.py     # 454 lines, MCP tool registration
├── test_health_endpoints.py  # 286 lines, HTTP health endpoints
├── test_logging_safety.py    # 179 lines, log sanitization
├── test_mcp_server_health_status.py # 60 lines, server status
└── test_pr_url_validation.py # 37 lines, URL validation
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Authentication tests** | `components/test_authentication.py` | API key hashing, env config, HMAC |
| **Rate limiter tests** | `components/test_rate_limiter.py` | Sliding window, thread safety |
| **Metrics tests** | `components/test_metrics_tracker.py` | Request tracking, timing stages |
| **PR handler tests** | `components/test_pr_operation_handler.py` | Mock services, domain interfaces |
| **Factory tests** | `factories/test_application_factory.py` | Singleton pattern, interface compliance |
| **URL parser tests** | `utils/test_pr_url_parser.py` | GitHub URL patterns, edge cases |
| **Tool registry tests** | `test_tool_registry.py` | MCP tool execution, error handling |

## CONVENTIONS

### DI Component Testing
- **Mock interfaces, not implementations**: Use `Mock(spec=LoggerServiceInterface)`
- **Constructor injection**: Pass mocks directly, test DI behavior
- **AsyncMock for async methods**: `mock.get = AsyncMock(return_value=None)`
- **Factory tests verify protocol compliance**: Check `hasattr(result, "method_name")`

### Environment Mocking
- **Use `@patch.dict(os.environ, {...})`** for environment variable tests
- **Reset between tests**: Environment patches auto-revert with context manager

### Component Test Patterns
- **Class-based organization**: `TestComponentInitialization`, `TestComponentMethods`
- **Descriptive test names**: `test_authentication_loads_api_keys`
- **Assert behavior, not internals**: Test public API, not private methods

### Fixtures (Local)
- **Component-specific fixtures** defined inline (not in conftest.py)
- **Standard mock pattern**: `mock_pr_diff_service`, `mock_cache_service`, `mock_logger`, `mock_rate_limiter`, `mock_metrics_tracker`

## ANTI-PATTERNS

- **NO real GitHub API calls** → Mock `PRDiffRepositoryInterface`
- **NO infrastructure imports in tests** → Mock domain interfaces only
- **NO shared state between tests** → Fresh mocks per test
- **NO testing private methods directly** → Test via public API
- **NO hardcoded API keys in tests** → Use test fixtures
- **NO bypassing authentication tests** → Full auth flow coverage required
