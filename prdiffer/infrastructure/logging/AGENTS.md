# AGENTS.md - Infrastructure/Logging

Logging infrastructure with sanitization and LazyLoggerMixin pattern.

## Guidelines

- **Never log sensitive data** (tokens, API keys, passwords)
- Use `sanitize_exception_for_logging()` for exceptions
- Structured logging with context
- Support multiple log levels
- **LazyLoggerMixin** to prevent circular imports (66-line pattern)

## Common Patterns

### LazyLoggerMixin (Circular Import Prevention)
```python
class LazyLoggerMixin:
    '''66-line mixin for lazy logger initialization (prevents circular imports)'''
    
    @property
    def _logger(self):
        '''Lazy initialization of logger instance'''
        if not hasattr(self, '_logger_instance'):
            from prdiffer.infrastructure.logging.logger_factory import LoggerFactory
            self._logger_instance = LoggerFactory.get_logger(self.__class__.__name__)
        return self._logger_instance

# Usage in infrastructure services
class GitHubAPIClient(LazyLoggerMixin):
    def get_repository(self, repo_name: str):
        self._logger.info(f'Fetching repository: {repo_name}')
        # ...
```

### Logger with Sanitization
```python
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)

class ConsoleLogger:
    def error(self, message: str, exception: Optional[Exception] = None) -> None:
        if exception:
            extra = sanitize_exception_for_logging(exception)
            print(f'ERROR: {message}', extra=extra)
        else:
            print(f'ERROR: {message}')
```

### Exception Sanitization (Remove Sensitive Data)
```python
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)

def safe_log_error(logger, message: str, exception: Exception) -> None:
    '''Remove tokens/API keys before logging'''
    sanitized = sanitize_exception_for_logging(exception)
    logger.error(message, extra=sanitized)
```

### Structured Logging with Context
```python
class StructuredLogger:
    def log_with_context(self, message: str, **context):
        '''Include context: request_id, user_id, trace_id'''
        log_data = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            **context
        }
        print(json.dumps(log_data))
```

## Anti-Patterns

- ❌ Logging sensitive data (tokens, passwords, API keys)
- ❌ Missing exception sanitization
- ❌ Circular imports (use LazyLoggerMixin instead)
- ❌ Unstructured logs (no context)
- ❌ Excessive logging in hot paths (performance)

## Files

- `console_logger.py`: Main logger implementation
- `exception_utils.py`: Exception sanitization utilities
- `logger_factory.py`: LazyLoggerMixin (66 lines, circular import prevention)
