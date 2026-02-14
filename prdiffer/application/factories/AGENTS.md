# AGENTS.md - Application/Factories

Application-layer component factory implementing dependency inversion.

## OVERVIEW
ApplicationFactory creates application components (RateLimiter, MetricsTracker, PROperationHandler, etc.) following domain interface contracts.

## STRUCTURE
```
prdiffer/application/factories/
├── application_factory.py  # ApplicationFactory (103 lines)
└── __init__.py             # Exports: ApplicationFactory, get_application_factory
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Create component** | `application_factory.py` | Factory methods for all components |
| **Singleton access** | `application_factory.py` | get_application_factory() |

## CONVENTIONS

### Factory Interface Implementation
```python
class ApplicationFactory(ApplicationFactoryInterface):
    '''Implements domain factory interface (dependency inversion)'''
    
    def create_rate_limiter(self, logger) -> RateLimiterProtocol:
        return RateLimiter(logger=logger)
    
    def create_metrics_tracker(self, logger) -> MetricsTrackerProtocol:
        return MetricsTracker(logger=logger)
```

### Components Created
| Method | Returns | Dependencies |
|--------|---------|--------------|
| `create_rate_limiter()` | RateLimiter | logger |
| `create_metrics_tracker()` | MetricsTracker | logger |
| `create_pr_operation_handler()` | PROperationHandler | github_repo, cache, logger, input_validator |
| `create_health_monitor()` | HealthMonitor | metrics_tracker, rate_limiter, logger |
| `create_server_configuration()` | ServerConfiguration | settings_service, logger |
| `create_authentication()` | AuthenticationMiddleware | logger |

### Singleton Pattern
```python
_application_factory: ApplicationFactory | None = None

def get_application_factory() -> ApplicationFactoryInterface:
    global _application_factory
    if _application_factory is None:
        _application_factory = ApplicationFactory()
    return _application_factory
```

## ANTI-PATTERNS

- NO direct component instantiation → Use factory methods
- NO circular imports → Factory imports from domain interfaces, not implementations
- NO missing DI → All dependencies passed via factory parameters

## Files

- `application_factory.py`: ApplicationFactory (103 lines)
