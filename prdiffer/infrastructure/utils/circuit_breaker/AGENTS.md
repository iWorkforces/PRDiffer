# AGENTS.md - Utils/CircuitBreaker

Fault tolerance with state machine pattern: CLOSED → OPEN → HALF_OPEN.

## OVERVIEW
CircuitBreaker for external API fault tolerance with configurable failure threshold and recovery timeout.

## STRUCTURE
```
prdiffer/infrastructure/utils/circuit_breaker/
├── core.py      # CircuitBreaker (224 lines), CircuitState enum
├── registry.py  # GlobalCircuitBreakerRegistry (276 lines)
└── __init__.py  # Exports: CircuitBreaker, CircuitState, GlobalCircuitBreakerRegistry
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Circuit breaker** | `core.py` | CircuitBreaker class |
| **State management** | `core.py` | CircuitState enum |
| **Global registry** | `registry.py` | GlobalCircuitBreakerRegistry |

## CONVENTIONS

### State Machine
```
CLOSED (normal) → OPEN (failures exceed threshold)
     ↑                    ↓
     └── HALF_OPEN ← (timeout elapsed)
           ↓
       CLOSED (success) or OPEN (failure)
```

### Dual Lock Pattern
```python
# Synchronous operations
self._lock = threading.Lock()

# Async operations (lazy init)
self._async_lock: anyio.Lock | None = None

async def _get_async_lock(self):
    if self._async_lock is None:
        self._async_lock = anyio.Lock()
    return self._async_lock
```

### Unlocked Method Pattern
```python
def _record_success_unlocked(self):
    '''Internal method called with lock already held'''
    self._failure_count = 0
    self._transition_closed_unlocked()
```

### Configuration
```python
CircuitBreaker(
    failure_threshold=5,  # Failures before opening
    timeout=60,           # Seconds before half-open
    success_threshold=1,  # Successes to close from half-open
)
```

## ANTI-PATTERNS

- NO bypassing circuit breaker → Always go through CircuitBreaker for external APIs
- NO missing state check → Call can_attempt() before operation
- NO ignoring half-open → Handle HALF_OPEN state appropriately

## Files

- `core.py`: CircuitBreaker, CircuitState (224 lines)
- `registry.py`: GlobalCircuitBreakerRegistry (276 lines)
