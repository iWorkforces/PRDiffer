# AGENTS.md - Domain/Factories

Factory patterns for creating domain objects.

## Guidelines

- Use factory functions or Factory classes
- Keep factories simple - just object creation
- Validate inputs before construction
- Return type hints required

## Common Patterns

### Factory Function
```python
from typing import Optional

def create_pr_diff(diff_content: str) -> PRDiff:
    if not diff_content:
        raise ValueError("Diff content cannot be empty")
    return PRDiff(diff_content=diff_content)
```

### Factory Class
```python
class PRDiffFactory:
    @staticmethod
    def from_files(files: List[FilePatchInfo]) -> PRDiff:
        combined_content = "\n".join(f.patch for f in files)
        return PRDiff(diff_content=combined_content)
```

## Files

- `infrastructure_factory.py`: Factory for infrastructure dependencies
