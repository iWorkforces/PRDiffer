# CLAUDE.md - Infrastructure Factories

This file provides guidance for working with the infrastructure factory implementations in CCPRAgents.

## Overview

The `factories/` directory contains concrete implementations of factory interfaces defined in the domain layer. The primary class `InfrastructureFactory` creates all infrastructure services with proper dependency injection and singleton patterns.

## Key Components

### InfrastructureFactory (`infrastructure_factory.py`)

Concrete implementation of `InfrastructureFactoryInterface` that creates real infrastructure service instances.

**Service Creation Methods:**

| Method | Returns | Implementation |
|--------|---------|----------------|
| `create_settings_service()` | `SettingsServiceInterface` | `get_settings_service()` singleton |
| `create_logger_service()` | `LoggerServiceInterface` | `get_logger()` singleton |
| `create_cache_service()` | `CacheServiceInterface` | `get_cache_service()` singleton |
| `create_repository_cache_service()` | `RepositoryCacheServiceInterface` | `get_repository_cache_service()` singleton |
| `create_github_api_service()` | `GitHubAPIServiceInterface` | `GitHubAPIClient()` new instance |
| `create_diff_service()` | `DiffServiceInterface` | `DiffUtils()` new instance |
| `create_pattern_matching_service()` | `PatternMatchingServiceInterface` | `PatternMatcher(...)` configured from settings |
| `create_retry_service()` | `RetryServiceInterface` | `RetryHandler()` new instance |
| `create_pr_diff_service()` | `PRDiffServiceInterface` | `GitHubPRDiffService(...)` with dependencies |

**Additional Factory Methods:**
- `create_file_processor()` - Creates `FileProcessor` for file filtering and validation
- `create_diff_generator()` - Creates `DiffGenerator` for diff content generation

**Application Component Factory Methods:**
- `create_rate_limiter(logger)` - Creates `RateLimiter`
- `create_metrics_tracker(logger)` - Creates `MetricsTracker`
- `create_pr_operation_handler(...)` - Creates `PROperationHandler`
- `create_health_monitor(...)` - Creates `HealthMonitor`
- `create_server_configuration(...)` - Creates `ServerConfiguration`

### Factory Function

```python
def get_infrastructure_factory() -> InfrastructureFactoryInterface:
    """Get infrastructure factory instance."""
    return InfrastructureFactory()
```

## File Structure

```
ccpragents/infrastructure/factories/
├── __init__.py                      # Package initialization
├── infrastructure_factory.py        # InfrastructureFactory implementation
└── CLAUDE.md                        # This file
```

## Design Patterns

### Factory Method Pattern

Each `create_*` method encapsulates the creation logic:

```python
def create_pattern_matching_service(self) -> PatternMatchingServiceInterface:
    settings_service = get_settings_service()
    github_settings = settings_service.get_github_settings()

    ignore_patterns = github_settings.get("ignore_patterns", [])
    valid_extensions = github_settings.get("valid_extensions", [])

    return PatternMatcher(
        ignore_patterns=list(ignore_patterns) if ignore_patterns else [],
        valid_extensions=list(valid_extensions) if valid_extensions else [],
    )
```

### Singleton Pattern

Core services use singleton patterns for shared state:
- `get_settings_service()` - Single configuration instance
- `get_logger()` - Single logging instance
- `get_cache_service()` - Single cache instance
- `get_repository_cache_service()` - Single repository cache

### Dependency Injection

Complex services receive their dependencies:

```python
def create_pr_diff_service(self) -> PRDiffServiceInterface:
    github_api_service = self.create_github_api_service()
    diff_service = self.create_diff_service()
    pattern_matching_service = self.create_pattern_matching_service()
    logger_service = self.create_logger_service()

    file_processor = FileProcessor(...)
    diff_generator = get_diff_generator(...)

    return GitHubPRDiffService(
        github_api_client=github_api_service,
        diff_generator=diff_generator,
        file_processor=file_processor,
        logger=logger_service,
    )
```

## Implementation Details

### Service Dependencies

The factory resolves the following dependency graph:

```
GitHubPRDiffService
├── GitHubAPIClient
├── DiffGenerator
│   └── DiffUtils
├── FileProcessor
│   ├── GitHubAPIClient
│   ├── PatternMatcher
│   │   └── SettingsService (for patterns)
│   └── DiffUtils
└── LoggerService
```

### Configuration Integration

Services requiring configuration access settings through `SettingsService`:
- `PatternMatcher` gets ignore patterns and valid extensions
- `DiffGenerator` may receive parallel processing settings
- Components use singleton settings for consistency

## Development Guidelines

### Adding New Services

1. Define interface in `domain/services/`
2. Implement service in appropriate infrastructure module
3. Add factory method to `InfrastructureFactoryInterface`
4. Implement factory method in `InfrastructureFactory`
5. Wire dependencies if needed

### Factory Method Conventions

- Return interface types, not concrete classes
- Use existing singletons for shared services
- Create new instances for stateful services
- Document dependency requirements

### Import Structure

```python
# Domain interfaces
from ccpragents.domain.factories.infrastructure_factory import InfrastructureFactoryInterface
from ccpragents.domain.services.* import *Interface

# Application protocols
from ccpragents.application.interfaces.protocols import *Protocol

# Infrastructure implementations
from ccpragents.infrastructure.* import ConcreteImplementation
```

## Integration Points

- **Domain Layer**: Implements `InfrastructureFactoryInterface`
- **Application Layer**: Used by `create_mcp_server()` factory
- **Infrastructure Services**: Creates instances from various infrastructure modules

## Testing

The factory pattern enables easy testing:

```python
# Production
factory = get_infrastructure_factory()
service = factory.create_cache_service()

# Testing - use mock factory or individual mocks
mock_factory = MockInfrastructureFactory()
mock_service = mock_factory.create_cache_service()
```

## Usage Example

```python
from ccpragents.infrastructure.factories.infrastructure_factory import (
    get_infrastructure_factory
)

# Get factory instance
factory = get_infrastructure_factory()

# Create services
logger = factory.create_logger_service()
cache = factory.create_cache_service()
pr_diff_service = factory.create_pr_diff_service()

# Use services
logger.info("Starting operation")
cached_data = cache.get("key")
```
