# AGENTS.md - Application Components Unit Tests

6 test files covering MCP server components: authentication, rate limiting, metrics, health monitoring, PR operations, server config.

## OVERVIEW
Component-level unit tests with mocked dependencies. Tests focus on orchestration logic, not business rules.

## STRUCTURE
```
tests/unit/application/components/
├── test_authentication.py           # JWT/API key auth (1145 lines, largest)
├── test_metrics_tracker.py          # Request timing, success rates
├── test_health_monitor.py           # Health checks, status reporting
├── test_pr_operation_handler.py     # PR get/approve operations
├── test_rate_limiter.py             # Per-client rate limiting
└── test_server_configuration.py     # Transport, port, host config
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Auth flow** | `test_authentication.py` → `TestJWTAuthentication`, `TestAPIKeyAuth` |
| **Rate limit** | `test_rate_limiter.py` → `TestRateLimitEnforcement` |
| **Metrics** | `test_metrics_tracker.py` → `TestMetricsCollection` |
| **Health check** | `test_health_monitor.py` → `TestHealthStatus` |
| **PR ops** | `test_pr_operation_handler.py` → `TestPROperations` |

## CONVENTIONS

### Component Test Pattern
```python
@pytest.fixture
def component():
    '''Create component with mocked dependencies'''
    mock_dep = Mock()
    return AuthenticationComponent(dependency=mock_dep)

def test_component_behavior(component):
    '''Test orchestration, not business logic'''
    result = component.authenticate(valid_token)
    assert result.is_authenticated
```

### Authentication Testing
- Test JWT validation (not parsing - that's infrastructure)
- Test API key hash comparison
- Test rate limit enforcement per client

### Metrics Testing
- Use `time.perf_counter()` for timing assertions
- Test aggregation: success_rate = successes / total
- Verify Prometheus format output

## ANTI-PATTERNS

- NO business logic in component tests → Domain layer only
- NO real I/O → Mock all infrastructure services
- NO asyncio → Use @pytest.mark.anyio with anyio primitives
- NO testing internal state → Test observable behavior
