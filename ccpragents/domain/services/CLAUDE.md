# CLAUDE.md - Domain Service Interfaces

This file provides guidance for working with the domain service interfaces of CCPRAgents.

## Overview

This directory contains abstract interface definitions for services used by the domain layer. These interfaces define contracts that infrastructure implementations must fulfill, following the Dependency Inversion Principle of Clean Architecture.

## Interface Categories

### Core Service Interfaces

#### CacheServiceInterface (`cache.py`)
Abstract interface for caching operations with commit-based invalidation.

**Key Methods:**
- `get(key: str) -> Optional[Any]` - Retrieve cached value
- `set(key: str, value: Any, commit_sha: str = None) -> None` - Store value with optional commit SHA
- `invalidate_by_commit(old_commit: str, new_commit: str) -> None` - Invalidate cache when commits change
- `clear() -> None` - Clear entire cache
- `size() -> int` - Get cache size

**Usage Pattern:**
```python
cache_service = get_cache_service()  # Infrastructure provides implementation
cached_data = cache_service.get("pr/123")
if not cached_data:
    data = expensive_operation()
    cache_service.set("pr/123", data, commit_sha="abc123")
```

#### LoggerServiceInterface (`logger.py`)
Abstract interface for structured logging operations.

**Key Methods:**
- `debug(message: str, **kwargs) -> None` - Debug level logging
- `info(message: str, **kwargs) -> None` - Information logging
- `warning(message: str, **kwargs) -> None` - Warning logging
- `error(message: str, **kwargs) -> None` - Error logging
- `critical(message: str, **kwargs) -> None` - Critical error logging

**Structured Logging Support:**
All methods support additional context via keyword arguments for structured logging.

#### SettingsServiceInterface (`settings.py`)
Abstract interface for configuration management.

**Key Methods:**
- `get(key: str, default: Any = None) -> Any` - Get configuration value
- `get_github_settings() -> Dict[str, Any]` - Get GitHub-specific settings
- `get_app_settings() -> Dict[str, Any]` - Get application settings
- `clear_cache() -> None` - Clear settings cache

### GitHub-Specific Interfaces

#### GitHubAPIServiceInterface (`github_api.py`)
Abstract interface for GitHub API operations.

**Repository Operations:**
- `initialize_client(github_token: Optional[str], timeout: int) -> None` - Initialize API client
- `get_repository(repo_full_name: str) -> Optional[Repository]` - Get repository instance
- `get_pull_request(repository: Repository, pr_number: int) -> Optional[PullRequest]` - Get PR instance

**File Operations:**
- `get_file_content(repository: Repository, file_path: str, branch: str) -> str` - Get single file content
- `get_files_content_batch(repository: Repository, file_paths: List[str], branch: str) -> Dict[str, str]` - Batch file retrieval

### Utility Service Interfaces

#### RetryServiceInterface (`retry.py`)
Abstract interface for retry operations with exponential backoff.

**Key Methods:**
- `execute_with_retry(func: Callable, *args, **kwargs) -> Any` - Execute function with retry logic

**Configuration:**
- Max retries, base delay, and timeout settings
- Rate limit detection and special handling
- Exponential backoff with jitter

#### PatternMatchingServiceInterface (`pattern_matching.py`)
Abstract interface for file pattern matching and validation.

**Key Methods:**
- `is_valid_file(filename: str) -> bool` - Check if file should be processed
- `filter_files(filenames: List[str]) -> List[str]` - Filter list of filenames

**Pattern Support:**
- Ignore patterns (wildcards, directories, exact matches)
- Valid extensions (whitelist of allowed file types)
- Pre-compiled regex patterns for performance

#### DiffServiceInterface (`diff.py`)
Abstract interface for diff generation and manipulation.

**Key Methods:**
- `build_full_file_patch(original_file_str: str, new_file_str: str) -> str` - Generate full-file unified diff
- `decode_if_bytes(content: Union[str, bytes, bytearray]) -> str` - Handle content encoding
- `extend_patch(original_file_str: str, patch_str: str, new_file_str: str = "") -> str` - Extend patch with full context

#### RepositoryCacheServiceInterface (`repository_cache.py`)
Abstract interface for repository instance caching.

**Key Methods:**
- `insert(repository: PRDiffRepository) -> bool` - Cache repository instance
- `retrieve(owner: str, name: str, pr_number: int) -> Optional[PRDiffRepository]` - Get cached repository
- `validate(owner: str, name: str, pr_number: int) -> bool` - Check if cached instance is valid
- `remove(owner: str, name: str, pr_number: int) -> bool` - Remove from cache
- `clear() -> None` - Clear entire cache
- `size() -> int` - Get cache size
- `stats() -> Dict[str, Any]` - Get cache statistics

## Design Principles

### Dependency Inversion Principle
```
High-level Domain Layer
         ↑ (depends on abstractions)
Interface Definitions (This Directory)
         ↑ (implemented by)
Low-level Infrastructure Layer
```

**Benefits:**
- Domain logic doesn't depend on implementation details
- Easy to swap implementations (testing, different providers)
- Infrastructure can evolve without affecting domain logic
- Clear contracts between layers

### Interface Segregation Principle
Each interface focuses on a specific concern:
- **Single Responsibility**: Each interface has one clear purpose
- **Client-Specific**: Interfaces tailored to client needs
- **Minimal Surface**: Only essential methods exposed
- **Cohesive**: Related methods grouped together

### Liskov Substitution Principle
All implementations of an interface must be interchangeable:
- **Behavioral Compatibility**: Same behavior for same inputs
- **Exception Compatibility**: Same exception types and conditions
- **Contract Compliance**: Honor pre/post-conditions
- **Performance Expectations**: Reasonable performance characteristics

## Implementation Guidelines

### Creating New Interfaces
1. **Domain-Driven**: Start with domain needs, not implementation capabilities
2. **Abstract Methods**: Use `@abstractmethod` decorator for required methods
3. **Type Hints**: Provide complete type annotations for all methods
4. **Documentation**: Comprehensive docstrings with examples
5. **Contract Definition**: Clear pre/post-conditions and exceptions

### Interface Design Patterns
```python
from abc import ABC, abstractmethod
from typing import Optional, Any

class ExampleServiceInterface(ABC):
    """Abstract interface for example operations."""

    @abstractmethod
    def required_operation(self, param: str) -> Optional[Any]:
        """Perform required operation with clear contract.

        Args:
            param: Input parameter with defined constraints

        Returns:
            Result or None if operation fails gracefully

        Raises:
            ValueError: If param doesn't meet requirements
        """
        pass

    def optional_operation(self, param: str) -> bool:
        """Optional operation with default implementation."""
        return True  # Default behavior
```

### Testing Interface Compliance
```python
import pytest
from abc import ABC

def test_interface_implementation():
    """Test that implementation follows interface contract."""
    service = ConcreteImplementation()

    # Test interface compliance
    assert isinstance(service, ExampleServiceInterface)

    # Test method availability
    assert hasattr(service, 'required_operation')
    assert callable(service.required_operation)

    # Test behavior compliance
    result = service.required_operation("valid_input")
    assert result is not None or result is None  # Contract allows both
```

## Infrastructure Integration

### Implementation Pattern
Infrastructure layer provides concrete implementations:
```python
# Infrastructure implementation
class ConcreteService(ServiceInterface):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def method_implementation(self, param: str) -> Any:
        # Actual implementation using external libraries
        return external_library.process(param)

# Factory function for dependency injection
def get_concrete_service() -> ServiceInterface:
    return ConcreteService(config=load_config())
```

### Dependency Injection
Services are injected into domain use cases:
```python
class DomainUseCase:
    def __init__(self,
                 service1: Service1Interface,
                 service2: Service2Interface):
        self.service1 = service1
        self.service2 = service2

    def execute(self) -> Result:
        # Use services through interfaces
        data = self.service1.get_data()
        processed = self.service2.process(data)
        return Result(processed)
```

## Testing Strategies

### Mock Implementations
Create mock implementations for testing:
```python
class MockCacheService(CacheServiceInterface):
    def __init__(self):
        self.data = {}

    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)

    def set(self, key: str, value: Any, commit_sha: str = None) -> None:
        self.data[key] = value
```

### Test Doubles
Different types of test implementations:
- **Stubs**: Return predetermined responses
- **Mocks**: Verify interactions and behavior
- **Fakes**: Simplified working implementations
- **Spies**: Record calls for verification

### Contract Testing
Ensure all implementations honor interface contracts:
```python
def test_service_contract():
    """Test that service implementation follows interface contract."""
    implementations = [
        ProductionService(),
        TestService(),
        MockService()
    ]

    for service in implementations:
        # Test contract compliance for each implementation
        verify_contract_compliance(service)
```

## Interface Evolution

### Versioning Strategy
- **Minor Changes**: Add optional methods with default implementations
- **Major Changes**: Create new interfaces, deprecate old ones gradually
- **Compatibility**: Maintain backward compatibility when possible
- **Migration**: Provide migration guides for breaking changes

### Extension Pattern
```python
class ExtendedServiceInterface(BaseServiceInterface):
    """Extended interface with additional capabilities."""

    @abstractmethod
    def new_operation(self, param: str) -> Any:
        """New operation added in extended interface."""
        pass
```

## File Organization

```
ccpragents/domain/services/
├── __init__.py              # Public API exports
├── cache.py                # Cache service interface
├── logger.py               # Logging service interface
├── settings.py             # Configuration service interface
├── github_api.py           # GitHub API service interface
├── retry.py                # Retry service interface
├── pattern_matching.py     # Pattern matching service interface
├── diff.py                 # Diff service interface
└── repository_cache.py     # Repository cache service interface
```

## Benefits of Interface-Driven Design

### Testability
- **Isolated Testing**: Test domain logic without external dependencies
- **Mock Implementations**: Easy to create test doubles
- **Contract Verification**: Ensure implementations meet requirements
- **Fast Tests**: No need for slow external services in unit tests

### Flexibility
- **Implementation Swapping**: Change implementations without affecting domain logic
- **Multiple Implementations**: Support different strategies (in-memory vs Redis cache)
- **Environment Adaptation**: Different implementations for dev/test/prod
- **Feature Toggles**: Enable/disable features through implementation choice

### Maintainability
- **Clear Contracts**: Explicit expectations and responsibilities
- **Loose Coupling**: Minimal dependencies between layers
- **Single Responsibility**: Each interface has a focused purpose
- **Evolution Support**: Add features without breaking existing code

These service interfaces form the foundation of CCPRAgents's Clean Architecture, enabling flexible, testable, and maintainable code while preserving the integrity of the domain layer.
