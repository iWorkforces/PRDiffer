# AGENTS.md - Domain/Entities

Domain models representing core business objects.

## Guidelines

- Use Pydantic BaseModel for data validation
- **Immutable by design:** Always `frozen=True` for dataclasses
- Include computed properties (@property) for derived values
- Add Field descriptions for API documentation
- Validation in `__init__` or using Pydantic validators
- **Use `tuple[T, ...]` for collections** (hashability in frozen dataclasses)

## Common Patterns

### Rich Entity (FilePatchInfo)
```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class FilePatchInfo:
    '''Rich entity with business logic (350+ lines)'''
    file_path: str
    patch_lines: tuple[str, ...]  # NOT list (frozen dataclass)
    additions: int
    deletions: int
    
    def validate(self) -> bool:
        '''Business validation logic'''
        return self.additions >= 0 and self.deletions >= 0
    
    def calculate_review_priority(self) -> int:
        '''Complex business logic'''
        return self.additions + self.deletions * 2
    
    @property
    def total_changes(self) -> int:
        return self.additions + self.deletions
```

### Anemic Entity (PRDiff)
```python
from pydantic import BaseModel, Field

class PRDiff(BaseModel):
    '''Anemic entity - data container only'''
    diff_content: str = Field(
        default='',
        description='Combined diff content for all files'
    )

    @property
    def has_content(self) -> bool:
        return bool(self.diff_content and self.diff_content.strip())
```

### Entity with Enum
```python
from enum import Enum
from pydantic import BaseModel

class EDIT_TYPE(str, Enum):
    ADDED = 'added'
    MODIFIED = 'modified'
    DELETED = 'deleted'

class FilePatchInfo(BaseModel):
    filename: str
    patch: str
    edit_type: EDIT_TYPE
```

## Anti-Patterns

- ❌ Using `list` in frozen dataclasses (not hashable)
- ❌ Mutable dataclasses (always use frozen=True)
- ❌ Business logic in anemic entities
- ❌ Missing computed properties for derived values
- ❌ External dependencies in domain entities

## Files

- `pr_diff.py`: PR diff content entity (anemic)
- `file_patch.py`: File patch information entity (rich, 350+ lines)
