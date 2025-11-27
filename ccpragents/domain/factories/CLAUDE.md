# CLAUDE.md - Domain Factories

This file provides guidance for working with the domain factory interfaces in CCPRAgents.

## Overview

The `factories/` directory contains abstract factory interfaces that enable dependency inversion in the Clean Architecture pattern. These interfaces define contracts for creating infrastructure services without coupling the domain layer to concrete implementations.

## Key Components

### InfrastructureFactoryInterface (`infrastructure_factory.py`)

Abstract factory interface that provides methods for creating all infrastructure services. This interface ensures the application layer can obtain service instances without depending on infrastructure implementations.

**Core Service Factory Methods:**
- `create_settings_service() -> SettingsServiceInterface` - Creates configuration management service
- `create_logger_service() -> LoggerServiceInterface` - Creates structured logging service
- `create_cache_service() -> CacheServiceInterface` - Creates caching service with commit-based invalidation
- `create_repository_cache_service() -> RepositoryCacheServiceInterface` - Creates repository instance cache

**GitHub Integration Factory Methods:**
- `create_github_api_service() -> GitHubAPIServiceInterface` - Creates GitHub API client
- `create_diff_service() -> DiffServiceInterface` - Creates diff generation utilities
- `create_pattern_matching_service() -> PatternMatchingServiceInterface` - Creates file pattern matcher
- `create_retry_service() -> RetryServiceInterface` - Creates retry logic handler
- `create_pr_diff_service() -> PRDiffServiceInterface` - Creates PR diff operations service

**Application Component Factory Methods:**
- `create_url_validator(logger) -> URLValidatorProtocol` - Creates URL validation component
- `create_rate_limiter(logger) -> RateLimiterProtocol` - Creates rate limiting component
- `create_metrics_tracker(logger) -> MetricsTrackerProtocol` - Creates metrics tracking component
- `create_pr_operation_handler(...) -> PROperationHandlerProtocol` - Creates PR operation handler
- `create_health_monitor(...) -> HealthMonitorProtocol` - Creates health monitoring component
- `create_server_configuration(...) -> ServerConfigurationProtocol` - Creates server configuration

## File Structure

```
ccpragents/domain/factories/
├── __init__.py                      # Package initialization
├── infrastructure_factory.py        # InfrastructureFactoryInterface definition
└── CLAUDE.md                        # This file
```

## Design Patterns

### Abstract Factory Pattern

The `InfrastructureFactoryInterface` implements the Abstract Factory pattern:
- **Abstraction**: Defines interface for creating families of related services
- **Flexibility**: Allows different factory implementations for testing vs production
- **Consistency**: Ensures all services are created through a single entry point

### Dependency Inversion Principle

```
Application Layer (uses factory interface)
         ↓
Domain Layer (defines InfrastructureFactoryInterface)
         ↑
Infrastructure Layer (implements InfrastructureFactory)
```

**Benefits:**
- Domain layer has no dependency on infrastructure
- Easy to swap implementations (e.g., mock factory for testing)
- Clear contracts for service creation

## Usage Example

```python
from ccpragents.domain.factories.infrastructure_factory import InfrastructureFactoryInterface

class ApplicationService:
    def __init__(self, factory: InfrastructureFactoryInterface):
        # Obtain services through the factory
        self.logger = factory.create_logger_service()
        self.cache = factory.create_cache_service()
        self.settings = factory.create_settings_service()
```

## Development Guidelines

### Adding New Factory Methods

When adding new service types:
1. Define the service interface in `domain/services/`
2. Add abstract factory method to `InfrastructureFactoryInterface`
3. Implement the method in `infrastructure/factories/infrastructure_factory.py`
4. Document the method's purpose and return type

### Interface Design

- All factory methods should return interface types, not concrete implementations
- Method names should follow the pattern `create_<service_name>_service()`
- Include type hints for all parameters and return types
- Document dependencies required by each factory method

## Integration Points

- **Domain Services**: Returns interfaces defined in `domain/services/`
- **Application Protocols**: Returns protocols defined in `application/interfaces/`
- **Infrastructure Factory**: Implemented by `infrastructure/factories/InfrastructureFactory`

## Testing

For unit testing, create a mock factory:

```python
class MockInfrastructureFactory(InfrastructureFactoryInterface):
    def create_logger_service(self) -> LoggerServiceInterface:
        return MockLogger()

    def create_cache_service(self) -> CacheServiceInterface:
        return MockCacheService()
    # ... implement all abstract methods with mocks
```

This factory pattern enables comprehensive testing without external dependencies.
