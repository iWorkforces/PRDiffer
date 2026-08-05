# AGENTS.md - Application/Factories

ApplicationFactory implements domain factory interface (~99 lines).

## STRUCTURE
```
prdiffer/application/factories/
├── application_factory.py  # ApplicationFactory + get_application_factory()
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Create components** | `application_factory.py` | rate limiter, metrics, PR ops, health, config, auth |
| **Singleton access** | `get_application_factory()` | |

## METHODS
| Method | Returns (Protocol) |
|--------|--------------------|
| `create_rate_limiter` | RateLimiterProtocol |
| `create_metrics_tracker` | MetricsTrackerProtocol |
| `create_pr_operation_handler` | PROperationHandlerProtocol |
| `create_health_monitor` | HealthMonitorProtocol |
| `create_server_configuration` | ServerConfigurationProtocol |
| `create_authentication` | AuthenticationProtocol |

## CONVENTIONS
- Depend on domain Protocols for return types.
- Keep construction free of global side effects where possible.

## ANTI-PATTERNS
- NO embedding business logic in factory methods.
