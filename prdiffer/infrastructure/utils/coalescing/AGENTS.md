# AGENTS.md - Request Coalescing

**Package:** 0.6.2  
Deduplicate concurrent identical async work.

## STRUCTURE
```
prdiffer/infrastructure/utils/coalescing/
└── service.py   # RequestCoalescingService (+ related types)

# Canonical flattened module (preferred for new imports):
prdiffer/infrastructure/utils/coalescing_service.py   # (220)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Coalesce concurrent work** | `coalescing_service.py` | `get_request_coalescing_service()` |
| **Package path** | `coalescing/service.py` | Keep imports consistent within a change set |

## CONVENTIONS
- anyio-based waiter tracking (`anyio.Event`).
- Bound max waiters (default 100) for DoS prevention.
- Used on PR diff tool path to collapse stampedes for identical keys.
- Propagate the same result/exception to all waiters on a key.

## ANTI-PATTERNS
- NO unbounded waiter lists.
- NO swallowing exceptions without propagating to all waiters.
- NO mixing package vs flattened import styles within the same feature change without intent.
