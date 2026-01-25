# AGENTS.md - Infrastructure/Utils

Utility functions and helpers.

## Guidelines

- Pure functions where possible
- No I/O operations
- Reusable across the codebase
- Well-documented with docstrings

## Common Patterns

### Utility Functions
```python
from typing import Dict, Any, Optional
import re

def parse_pr_url(url: str) -> Optional[Dict[str, str]]:
    """Parse GitHub PR URL into components."""
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if match:
        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "pr_number": int(match.group(3)),
        }
    return None
```

### Retry Handler
```python
from typing import Callable, TypeVar, Optional
import time

T = TypeVar('T')

def retry(
    func: Callable[[], T],
    max_retries: int = 3,
    delay: float = 1.0,
) -> Optional[T]:
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))
    return None
```

## Files

- `retry_handler.py`: Retry logic with backoff
- `circuit_breaker.py`: Circuit breaker pattern
- `cache_decorator.py`: Caching decorators
- `diff_utils.py`: Diff processing utilities
- `diff_limits.py`: Diff size limits
- `pattern_matcher.py`: Pattern matching utilities
- `api_health_tracker.py`: API health monitoring
