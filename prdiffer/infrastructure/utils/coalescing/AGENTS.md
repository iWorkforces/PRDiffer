# AGENTS.md - Request Coalescing

Deduplicate concurrent identical async work (~221 lines in package).

## STRUCTURE
```
prdiffer/infrastructure/utils/coalescing/
└── service.py   # RequestCoalescingService (+ related types)
```

Also available as flattened-style module: `prdiffer/infrastructure/utils/coalescing_service.py` (keep imports consistent within a change set).

## CONVENTIONS
- anyio-based waiter tracking.
- Bound max waiters (DoS prevention).
- Used by PR diff tool path to collapse stampedes.

## ANTI-PATTERNS
- NO unbounded waiter lists.
- NO swallowing exceptions without propagating to all waiters.
