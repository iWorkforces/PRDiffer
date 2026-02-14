# AGENTS.md - Utils/Retry

Unified retry infrastructure with context-aware configuration, circuit breaker integration.

## OVERVIEW
Retry logic with exponential backoff, jitter, adaptive delays, and OperationContext enum for context-specific configs.

## STRUCTURE
```
prdiffer/infrastructure/utils/retry/
├── base.py        # BaseUnifiedRetryHandler (408 lines, LazyLoggerMixin)
├── handler.py     # UnifiedRetryHandler (136 lines, concrete impl)
├── models.py      # OperationContext enum, RETRY_EXCEPTIONS tuple
├── factories.py   # get_retry_handler(), get_advanced_retry_handler()
└── __init__.py    # Exports: UnifiedRetryHandler, OperationContext, factories
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Retry logic** | `handler.py` | UnifiedRetryHandler with sync/async |
| **Base class** | `base.py` | BaseUnifiedRetryHandler (circuit breaker, health tracker) |
| **Context config** | `base.py` | OperationContext enum for context-aware settings |
| **Factory** | `factories.py` | get_retry_handler(), get_advanced_retry_handler() |

## CONVENTIONS

### OperationContext Enum
```python
class OperationContext(StrEnum):
    FILE_CONTENT = "file_content"    # Never retry 404s
    PR_METADATA = "pr_metadata"      # Standard retry
    REPOSITORY = "repository"        # Aggressive retry
```

### Context-Aware Configuration
```python
# Different retry configs per operation type
self._context_configs = {
    OperationContext.FILE_CONTENT: {"retry_on_404": False},
    OperationContext.PR_METADATA: {"retry_on_404": True},
}
```

### Dual Sync/Async APIs
```python
# Synchronous
result = retry_handler.retry_sync(func, context=OperationContext.PR_METADATA)

# Asynchronous
result = await retry_handler.retry_async(func, context=OperationContext.FILE_CONTENT)
```

### Integration Points
- **Circuit Breaker**: Lazy initialization, opens on N failures
- **API Health Tracker**: Optional, tracks API health for adaptive retry
- **Error Classifier**: Categorizes exceptions for retry decisions

### RETRY_EXCEPTIONS Tuple
```python
RETRY_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
    # ... 21 total exception types
)
```

## ANTI-PATTERNS

- NO retrying 404s for file content → Not transient, file was added/removed
- NO infinite retry → Always set max_retries
- NO missing context → Use OperationContext for appropriate config
- NO bypassing circuit breaker → Always go through retry handler

## Files

- `base.py`: BaseUnifiedRetryHandler (408 lines)
- `handler.py`: UnifiedRetryHandler (136 lines)
- `models.py`: OperationContext enum, RETRY_EXCEPTIONS
- `factories.py`: Factory functions
