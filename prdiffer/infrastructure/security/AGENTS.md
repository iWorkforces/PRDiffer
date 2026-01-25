# AGENTS.md - Infrastructure/Security

Security utilities: input validation, sanitization, authentication.

## Guidelines

- Validate all inputs from external sources
- Sanitize user-provided data
- Use parameterized queries (no raw SQL)
- Hash sensitive data appropriately
- Reject suspicious patterns

## Common Patterns

### Input Validator
```python
from prdiffer.domain.exceptions import ValidationError

class InputValidator:
    @staticmethod
    def validate_pr_url(url: str) -> None:
        if not url.startswith("https://github.com/"):
            raise ValidationError("Invalid GitHub PR URL format")
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        # Remove dangerous patterns
        return text.replace("<script>", "").strip()
```

### Pattern Detection
```python
import re

SUSPICIOUS_PATTERNS = [
    r"(\$\([^)]+\))",  # Command injection
    r"('|;|--)",  # SQL injection
    r"(\.\./)",  # Path traversal
]

def check_suspicious_input(text: str) -> bool:
    return any(re.search(p, text) for p in SUSPICIOUS_PATTERNS)
```

## Files

- `input_validator.py`: Input validation and sanitization
