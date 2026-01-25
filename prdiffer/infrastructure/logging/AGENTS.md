# AGENTS.md - Infrastructure/Logging

Logging infrastructure with sanitization.

## Guidelines

- Never log sensitive data (tokens, API keys)
- Use `sanitize_exception_for_logging()` for exceptions
- Structured logging with context
- Support multiple log levels

## Common Patterns

### Logger with Sanitization
```python
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)

class ConsoleLogger:
    def error(self, message: str, **kwargs) -> None:
        extra = sanitize_exception_for_logging(kwargs.get('exception'))
        print(f"ERROR: {message}", extra=extra)
```

### Exception Sanitization
```python
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)

def safe_log_error(logger, message: str, exception: Exception) -> None:
    sanitized = sanitize_exception_for_logging(exception)
    logger.error(message, extra=sanitized)
```

## Files

- `console_logger.py`: Main logger implementation
- `exception_utils.py`: Exception sanitization utilities
