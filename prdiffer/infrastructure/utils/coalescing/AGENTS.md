# AGENTS.md - Request Coalescing

**Package:** 0.6.2  
Deduplicate concurrent identical async work.

## STRUCTURE
```
# Canonical implementation (preferred imports):
prdiffer/infrastructure/utils/coalescing_service.py

# Package path is a pure re-export shim (circuit-breaker pattern):
prdiffer/infrastructure/utils/coalescing/
├── __init__.py   # re-exports from coalescing_service
└── service.py    # re-exports from coalescing_service
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Coalesce concurrent work** | `../coalescing_service.py` | `RequestCoalescingService`, `get_request_coalescing_service()` |
| **Package imports** | `coalescing/` | Identical class/singleton identity via re-export |

## CONVENTIONS
- anyio-based waiter tracking (`anyio.Event`).
- Bound max waiters (default 100) for DoS prevention.
- Used on PR diff tool path to collapse stampedes for identical keys (host-aware for GitLab).
- Propagate the same result/exception/cancellation to all waiters on a key.
- Owner cancellation: shielded publish of terminal exception, signal event, remove exact owner entry, re-raise; waiters terminate and pending/waiter counts return to zero.
- Same-key request after cancelled owner executes a fresh fetch.

## ANTI-PATTERNS
- NO unbounded waiter lists.
- NO swallowing owner cancellation without notifying waiters.
- NO second divergent implementation inside the shim package.
- NO leaving pending keys after cancel/timeout/failure.
