# AGENTS.md - Request Coalescing

Request deduplication utility. Multiple concurrent requests for same resource → single fetch, shared result.

## OVERVIEW

2 files: `service.py` (255 lines), `__init__.py` (15 lines). Prevents thundering herd on popular PRs.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Deduplicate requests** | `service.py:RequestCoalescingService.coalesce()` | Main entry point |
| **Get singleton** | `service.py:get_request_coalescing_service()` | Global instance |
| **Stats/debug** | `service.py:get_stats()` | Pending count, keys, waiters |

## CONVENTIONS

### Lock + Dict Pattern
```python
_pending_requests: dict[str, CoalescedRequest] = {}
_lock = anyio.Lock()

async with self._lock:
    if key in self._pending_requests:
        pending.request_count += 1  # Join existing
        existing_request = pending
    else:
        new_request = CoalescedRequest(key=key)
        self._pending_requests[key] = new_request  # Become leader
```

### Waiter Signaling
- **anyio.Event** for single producer, multiple consumers
- Leader sets `result` or `exception`, then `event.set()`
- Waiters call `event.wait()`, read shared result
- Timeout via `anyio.fail_after()`

### Memory Safety
- `max_waiters` limit (default 100) prevents unbounded growth
- Excess waiters spawn new request instead of queueing
- Cleanup on all paths: success, failure, timeout, cancellation
- Atomic state transitions under lock

### Global Singleton
```python
_request_coalescing_service: RequestCoalescingService | None = None

def get_request_coalescing_service() -> RequestCoalescingService:
    global _request_coalescing_service
    if _request_coalescing_service is None:
        _request_coalescing_service = RequestCoalescingService()
    return _request_coalescing_service
```

## ANTI-PATTERNS

- **NO asyncio.Event** → Use anyio.Event (backend-agnostic)
- **NO unbounded waiters** → Enforce max_waiters limit
- **NO missing cleanup** → All exit paths must decrement/clear
- **NO blocking under lock** → Lock only for dict mutations, not fetch
- **NO direct Application import** → 4 violations exist (should use DI)

## KEY SYMBOLS

| Symbol | Type | Role |
|--------|------|------|
| `RequestCoalescingService` | Class | Main coalescing service |
| `CoalescedRequest` | Dataclass | Request state (key, event, result, exception, count) |
| `coalesce()` | Method | Deduplication entry point |
| `_wait_for_request()` | Method | Waiter path |
| `_execute_request()` | Method | Leader path |
