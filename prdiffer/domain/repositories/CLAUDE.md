# CLAUDE.md - Domain Repository Interfaces

This file provides guidance for working with the Domain Repository Interfaces in PRDiffer.

**Current Version:** 0.4.8

## Repository Interfaces Overview

The `repositories/` directory contains abstract interfaces that define the contracts for data access operations. These interfaces follow the Dependency Inversion Principle - they define what operations are available, not how they are implemented.

## Key Components

### PRDiffRepositoryInterface (`pr_diff_repository.py`)

The main repository interface for pull request diff operations:

**Properties:**
- `repo_owner`: Repository owner/organization name
- `repo_name`: Repository name  
- `pr_number`: Pull request number

**Methods:**
- `async get_pr_diff() -> PRDiff`: Get complete PR diff data
- `get_latest_commit_sha() -> str`: Get latest head commit SHA for cache invalidation

## Architecture Role

### Interface Definition
Repository interfaces define the contract between:
- **Domain Layer**: Business logic that needs data access
- **Infrastructure Layer**: Concrete implementations that provide data

### Dependency Inversion
- **Domain depends on abstractions**: Use cases depend on `PRDiffRepositoryInterface`
- **Infrastructure implements interfaces**: `GitHubPRDiffRepository` implements the interface
- **No circular dependencies**: Domain knows nothing about infrastructure details

## Implementation Guidelines

### When Creating New Repository Interfaces
1. **Define the contract**: What data operations are needed?
2. **Use abstract methods**: Mark methods with `@abstractmethod`
3. **Provide clear documentation**: Document parameters, returns, and behavior
4. **Keep interfaces focused**: Single responsibility principle
5. **Use async/await**: For I/O operations that may block

### Interface Design Patterns
- **Property-based access**: For immutable repository configuration
- **Async methods**: For data retrieval operations
- **Sync methods**: For simple metadata operations
- **Return domain entities**: Always return domain objects, not infrastructure models

## Example Usage Pattern

```python
# Domain use case depends on interface
class GetPRDiffUseCase:
    def __init__(self, repository: PRDiffRepositoryInterface):
        self.repository = repository
    
    async def execute(self) -> PRDiff:
        return await self.repository.get_pr_diff()

# Infrastructure implements interface
class GitHubPRDiffRepository(PRDiffRepositoryInterface):
    def __init__(self, owner: str, repo: str, pr_number: int):
        self._owner = owner
        self._repo = repo
        self._pr_number = pr_number
    
    @property
    def repo_owner(self) -> str:
        return self._owner
    
    @property 
    def repo_name(self) -> str:
        return self._repo
    
    @property
    def pr_number(self) -> int:
        return self._pr_number
    
    async def get_pr_diff(self) -> PRDiff:
        # Implementation using GitHub API
        pass
    
    def get_latest_commit_sha(self) -> str:
        # Implementation to get latest commit
        pass
```

## Testing Considerations

### Mocking Interfaces
Repository interfaces enable easy testing through mocking:

```python
# In tests, mock the interface
mock_repository = Mock(spec=PRDiffRepositoryInterface)
mock_repository.get_pr_diff.return_value = test_pr_diff_data

# Test use case with mock
use_case = GetPRDiffUseCase(mock_repository)
result = await use_case.execute()

# Verify interactions
mock_repository.get_pr_diff.assert_called_once()
```

### Interface Compliance Testing
Ensure implementations properly adhere to the interface:

```python
def test_repository_implements_interface():
    repository = GitHubPRDiffRepository("owner", "repo", 123)
    assert isinstance(repository, PRDiffRepositoryInterface)
    
    # Test all required methods exist
    assert hasattr(repository, 'repo_owner')
    assert hasattr(repository, 'repo_name') 
    assert hasattr(repository, 'pr_number')
    assert hasattr(repository, 'get_pr_diff')
    assert hasattr(repository, 'get_latest_commit_sha')
```

## Extension Patterns

### Adding New Repository Interfaces
When new data access needs arise:

1. **Create new interface file**: `new_repository_interface.py`
2. **Define abstract methods**: Required operations with proper typing
3. **Update domain layer**: Use new interface in use cases
4. **Implement in infrastructure**: Create concrete implementation

### Interface Versioning
- **Backward compatible**: Add new methods, don't remove existing ones
- **Optional methods**: Use `@abstractmethod` only for required operations
- **Default implementations**: Consider abstract base classes with mixins

## Best Practices

### Interface Design
- **Minimal interface**: Only define methods actually needed
- **Clear contracts**: Document expected behavior and error conditions
- **Consistent naming**: Follow existing patterns (`get_`, `create_`, `update_`)
- **Proper typing**: Use Python type hints for all parameters and returns

### Implementation Guidelines
- **Loose coupling**: Interfaces should not depend on implementation details
- **Testability**: Design interfaces to be easily mockable
- **Error handling**: Define expected error behavior in interface documentation
- **Performance considerations**: Document any performance characteristics

This interface-based approach enables clean separation of concerns, easy testing, and flexible implementation swapping while maintaining strong contracts between domain and infrastructure layers.