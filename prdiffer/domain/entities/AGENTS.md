# AGENTS.md - Domain/Entities

Domain models representing core business objects.

## Guidelines

- Use Pydantic BaseModel for data validation
- Immutable by design (frozen=True when appropriate)
- Include computed properties (@property)
- Add Field descriptions for API documentation
- Validation in `__init__` or using Pydantic validators

## Common Patterns

### Basic Entity
```python
from pydantic import BaseModel, Field

class PRDiff(BaseModel):
    diff_content: str = Field(
        default="",
        description="Combined diff content for all files"
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
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"

class FilePatchInfo(BaseModel):
    filename: str
    patch: str
    edit_type: EDIT_TYPE
```

## Files

- `pr_diff.py`: PR diff content entity
- `file_patch.py`: File patch information entity
