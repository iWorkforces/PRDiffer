# CLAUDE.md - Domain Use Cases

This file provides guidance for working with the domain use cases of CCPRAgents.

## Overview

This directory contains the business logic orchestration layer of the domain. Use cases represent the application-specific business rules and coordinate between entities and services to fulfill business requirements. They are the entry points for all business operations in the system.

## Use Case Components

### PRDiffRepository Interface (`pr_diff_usecases.py`)

**PRDiffRepository**
Abstract base class defining the contract for PR diff data retrieval. This interface follows the Repository pattern and represents the boundary between the domain and infrastructure layers.

**Interface Definition:**
```python
class PRDiffRepository(ABC):
    @abstractmethod
    async def get_pr_diff(self) -> ExtraPRDiff:
        """Fetch PR diff information from the source.
        
        Returns:
            ExtraPRDiff: Complete PR information with diff content
        """
        pass
```

**Key Characteristics:**
- **Async Interface**: Supports asynchronous operations for I/O bound tasks
- **Single Responsibility**: Focused solely on PR diff retrieval
- **Implementation Agnostic**: Can be implemented by any data source (GitHub, GitLab, local files)
- **Domain Boundary**: Separates business logic from data access concerns

### GetPRDiffUseCase

**GetPRDiffUseCase**
The primary use case orchestrating PR diff retrieval with optional caching and validation.

**Key Responsibilities:**
- **Repository Coordination**: Delegates data retrieval to repository implementation
- **Cache Management**: Integrates with cache service for performance optimization
- **Business Rule Enforcement**: Applies domain-specific validation and processing rules
- **Error Handling**: Provides graceful error handling and recovery strategies

**Constructor Dependencies:**
```python
def __init__(self, 
             repository: PRDiffRepository,
             cache_service: Optional[CacheServiceInterface] = None,
             settings_service: Optional[SettingsServiceInterface] = None):
```

**Execution Flow:**
1. **Cache Check**: Check if cached data exists for the PR
2. **Cache Validation**: Verify cached data is still valid (commit SHA comparison)
3. **Repository Call**: Fetch fresh data if cache miss or invalid
4. **Data Processing**: Apply business rules and transformations
5. **Cache Update**: Store fresh data for future requests
6. **Result Return**: Return processed ExtraPRDiff entity

## Architecture Patterns

### Use Case Pattern
Use cases implement the Use Case pattern from Clean Architecture:
- **Single Purpose**: Each use case handles one business scenario
- **Dependency Inversion**: Depends on abstractions (interfaces) not implementations
- **Business Logic Container**: Contains application-specific business rules
- **Orchestration**: Coordinates between entities, services, and repositories

### Repository Pattern
The repository interface implements the Repository pattern:
- **Data Access Abstraction**: Hides data source implementation details
- **Domain-Centric**: Expressed in domain terms, not data source terms
- **Testability**: Easy to mock for unit testing
- **Implementation Flexibility**: Can switch data sources without changing use cases

### Dependency Injection
Use cases receive dependencies through constructor injection:
```python
# Production wiring
repository = GitHubPRDiffRepository("owner", "repo", 123)
cache_service = get_cache_service()
use_case = GetPRDiffUseCase(repository, cache_service)

# Test wiring
mock_repository = MockPRDiffRepository()
mock_cache = MockCacheService()
use_case = GetPRDiffUseCase(mock_repository, mock_cache)
```

## Business Logic Implementation

### Caching Strategy
The use case implements intelligent caching based on commit SHAs:

```python
async def execute(self, use_cache: bool = True) -> ExtraPRDiff:
    if not use_cache or not self.cache_service:
        return await self.repository.get_pr_diff()
    
    # Check cache for existing data
    cache_key = self._generate_cache_key()
    cached_data = self.cache_service.get(cache_key)
    
    if cached_data:
        # Validate cached data against current commit
        current_commit = self.repository.get_latest_commit_sha()
        if cached_data.get('commit_sha') == current_commit:
            return cached_data['pr_diff']
    
    # Fetch fresh data and cache it
    pr_diff = await self.repository.get_pr_diff()
    self._cache_result(cache_key, pr_diff)
    return pr_diff
```

### Validation Rules
Use cases enforce business rules and validation:
- **Data Completeness**: Ensure required fields are present
- **Business Constraints**: Apply domain-specific constraints
- **Data Consistency**: Verify internal consistency of data
- **Security Rules**: Apply security and access control rules

### Error Handling Strategy
Comprehensive error handling with graceful degradation:
```python
try:
    pr_diff = await self.repository.get_pr_diff()
except GitHubAPIError as e:
    # Log error and return cached data if available
    logger.error(f"GitHub API error: {e}")
    return self._get_cached_fallback()
except Exception as e:
    # Log unexpected errors and re-raise
    logger.error(f"Unexpected error in GetPRDiffUseCase: {e}")
    raise
```

## Use Case Lifecycle

### Initialization Phase
1. **Dependency Validation**: Ensure all required dependencies are provided
2. **Configuration Loading**: Load relevant settings and configuration
3. **Service Initialization**: Initialize any internal services or state
4. **Validation Setup**: Set up validation rules and constraints

### Execution Phase
1. **Input Validation**: Validate input parameters and preconditions
2. **Business Logic Execution**: Execute core business logic
3. **Service Coordination**: Coordinate with external services and repositories
4. **Result Processing**: Process and validate results
5. **Side Effects**: Handle caching, logging, and other side effects

### Cleanup Phase
1. **Resource Cleanup**: Clean up resources and connections
2. **Cache Management**: Update caches with new data
3. **Audit Logging**: Log business events for audit trails
4. **Error Reporting**: Report any issues or anomalies

## Testing Strategies

### Unit Testing Use Cases
```python
async def test_get_pr_diff_cache_hit():
    # Arrange
    mock_repo = Mock(spec=PRDiffRepository)
    mock_cache = Mock(spec=CacheServiceInterface)
    
    expected_pr_diff = ExtraPRDiff(pr_number=123, ...)
    mock_cache.get.return_value = {
        'commit_sha': 'abc123',
        'pr_diff': expected_pr_diff
    }
    mock_repo.get_latest_commit_sha.return_value = 'abc123'
    
    use_case = GetPRDiffUseCase(mock_repo, mock_cache)
    
    # Act
    result = await use_case.execute(use_cache=True)
    
    # Assert
    assert result == expected_pr_diff
    mock_repo.get_pr_diff.assert_not_called()  # Should use cache
    mock_cache.get.assert_called_once()
```

### Integration Testing
```python
async def test_get_pr_diff_integration():
    # Use real repository implementation with test data
    repository = GitHubPRDiffRepository("test-owner", "test-repo", 1)
    cache_service = InMemoryCacheService()
    
    use_case = GetPRDiffUseCase(repository, cache_service)
    result = await use_case.execute()
    
    assert isinstance(result, ExtraPRDiff)
    assert result.pr_number == 1
    assert result.repo_owner == "test-owner"
    assert result.repo_name == "test-repo"
```

### Error Scenario Testing
```python
async def test_get_pr_diff_repository_failure():
    mock_repo = Mock(spec=PRDiffRepository)
    mock_repo.get_pr_diff.side_effect = GitHubAPIError("Rate limit exceeded")
    
    use_case = GetPRDiffUseCase(mock_repo)
    
    with pytest.raises(GitHubAPIError):
        await use_case.execute()
```

## Extension Guidelines

### Adding New Use Cases
1. **Identify Business Need**: Clearly define the business scenario
2. **Define Interface**: Create repository interfaces if needed
3. **Implement Use Case**: Create use case class with proper error handling
4. **Add Dependencies**: Identify and inject required services
5. **Write Tests**: Comprehensive unit and integration tests
6. **Document**: Add documentation and usage examples

### Modifying Existing Use Cases
1. **Backward Compatibility**: Ensure changes don't break existing clients
2. **Parameter Evolution**: Use optional parameters for new functionality
3. **Error Handling**: Maintain existing error handling contracts
4. **Performance**: Consider performance implications of changes
5. **Testing**: Update tests to cover new functionality

### Best Practices
- **Single Responsibility**: Each use case should handle one business scenario
- **Dependency Injection**: Accept dependencies through constructor
- **Async/Await**: Use async/await for I/O bound operations
- **Error Handling**: Provide comprehensive error handling with meaningful messages
- **Logging**: Add structured logging for debugging and monitoring
- **Validation**: Validate inputs and enforce business rules
- **Testing**: Maintain high test coverage with unit and integration tests

## Performance Considerations

### Caching Strategy
- **Commit-Based Invalidation**: Cache invalidated when PR commits change
- **TTL Fallback**: Use time-based expiration as fallback
- **Cache Warming**: Pre-populate cache for frequently accessed PRs
- **Memory Management**: Monitor cache size and implement eviction policies

### Resource Management
- **Connection Pooling**: Reuse expensive resources like HTTP connections
- **Rate Limiting**: Respect external service rate limits
- **Timeout Handling**: Set appropriate timeouts for external calls
- **Resource Cleanup**: Properly clean up resources in error scenarios

### Scalability
- **Stateless Design**: Use cases should be stateless for horizontal scaling
- **Async Operations**: Use async/await for concurrent processing
- **Batch Processing**: Support batch operations when possible
- **Resource Monitoring**: Monitor resource usage and performance metrics

## File Organization

```
ccpragents/domain/usecases/
├── __init__.py              # Public API exports
└── pr_diff_usecases.py     # PR diff use case and repository interface
```

## Integration with Other Layers

### Application Layer Integration
Application layer creates and executes use cases:
```python
# Application layer (MCP server)
class FastMCPServer:
    def __init__(self):
        self.repository = GitHubPRDiffRepository(...)
        self.cache_service = get_cache_service()
        self.use_case = GetPRDiffUseCase(self.repository, self.cache_service)
    
    async def get_pr_diff_tool(self, url: str) -> str:
        pr_diff = await self.use_case.execute()
        return serialize_pr_diff(pr_diff)
```

### Infrastructure Layer Dependencies
Use cases depend on infrastructure implementations:
- **Repository Implementation**: GitHubPRDiffRepository provides data access
- **Cache Service**: InMemoryCacheService or RedisCacheService for caching
- **Settings Service**: ConfigurationService for settings
- **Logger Service**: ConsoleLogger for structured logging

This use case layer provides a clean separation between business logic and implementation details, enabling testable, maintainable, and flexible application architecture.