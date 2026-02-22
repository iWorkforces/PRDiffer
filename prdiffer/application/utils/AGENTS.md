# AGENTS.md - Application Utils

URL parsing utilities for PR diff operations.

## OVERVIEW

Single module for GitHub PR URL parsing. Consolidates URL extraction logic used by FastMCPServer and PROperationHandler.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Parse PR URL** | `pr_url_parser.py:parse_pr_url()` | Returns `(owner, repo, pr_number)` tuple |
| **URL validation** | Delegated to `InputValidator` | Architecture violation - see below |

## STRUCTURE

```
prdiffer/application/utils/
├── __init__.py           # Exports parse_pr_url
└── pr_url_parser.py      # 58 lines, URL extraction logic
```

## CONVENTIONS

### URL Parsing Pattern

```python
# Input
"https://github.com/owner/repo/pull/123"

# Output
("owner", "repo", 123)  # tuple[str, str, int]
```

### Function Signature

```python
def parse_pr_url(
    pr_url: str,
    input_validator: InputValidator | None = None,
) -> tuple[str, str, int]:
```

- Optional `input_validator` for DI/testability
- Validates: not None, is string, not empty/whitespace
- Delegates to `InputValidator.validate_github_url()`

### Exceptions Raised

- `InvalidURLError`: None, wrong type, empty/whitespace
- `SuspiciousOperationError`: Injection patterns detected
- `InvalidRepositoryError`: Invalid repo name
- `InvalidPRNumberError`: Invalid PR number

## ANTI-PATTERNS

### ARCHITECTURE VIOLATION (Line 11)

```python
from prdiffer.infrastructure.security.input_validator import InputValidator
```

**Problem:** Application layer directly imports Infrastructure module.

**Fix:** Define `SecurityService` interface in Domain, inject via DI.

**Current workaround:** Optional `input_validator` parameter allows mocking in tests.
