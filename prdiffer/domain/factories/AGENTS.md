# AGENTS.md - Domain/Factories

Factory patterns for creating domain objects.

## Guidelines

- Use factory functions or Factory classes
- Keep factories simple - just object creation
- Validate inputs before construction
- Return type hints required
- **Dual factory pattern:** Domain defines interface, infrastructure implements
- **Dependency inversion:** Factories return interfaces, not concrete types

## Common Patterns

### Factory Function
```python
from typing import Optional

def create_pr_diff(diff_content: str) -> PRDiff:
    if not diff_content:
        raise ValueError('Diff content cannot be empty')
    return PRDiff(diff_content=diff_content)
```

### Factory Class
```python
class PRDiffFactory:
    @staticmethod
    def from_files(files: tuple[FilePatchInfo, ...]) -> PRDiff:
        combined_content = '\n'.join(f.patch for f in files)
        return PRDiff(diff_content=combined_content)
```

### Infrastructure Factory Interface (Dependency Inversion)
```python
from abc import ABC, abstractmethod

class InfrastructureFactoryInterface(ABC):
    '''Domain defines interface, infrastructure implements'''
    
    @abstractmethod
    def create_github_service(self) -> GitHubAPIServiceInterface:
        '''Return interface, not concrete type'''
        pass
    
    @abstractmethod
    def create_cache_service(self) -> CacheServiceInterface:
        pass
```

## Anti-Patterns

- ❌ Complex logic in factories (keep simple)
- ❌ Returning concrete types from factory interfaces
- ❌ Missing input validation
- ❌ Factory methods with side effects

## Files

- `infrastructure_factory.py`: Factory interface for infrastructure dependencies
