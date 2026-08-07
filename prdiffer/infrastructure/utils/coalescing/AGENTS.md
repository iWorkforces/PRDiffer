# AGENTS.md - Request Coalescing

**Package:** 0.6.2  
Deduplicate concurrent identical async work.

## STRUCTURE
```
# Canonical flattened module (preferred — always use this):
prdiffer/infrastructure/utils/coalescing_service.py   # (~220)

# Package path is a FULL DUPLICATE of the flattened module (not a re-export shim):
prdiffer/infrastructure/utils/coalescing/
└── service.py   # identical copy of coalescing_service.py (~220)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Coalesce concurrent work** | `../coalescing_service.py` | `get_request_coalescing_service()` — **only** import this path |
| **Package path** | `coalescing/service.py` | Legacy duplicate; do not import in new code |

## CONVENTIONS
- anyio-based waiter tracking (`anyio.Event`).
- Bound max waiters (default 100) for DoS prevention.
- Used on PR diff tool path to collapse stampedes for identical keys (host-aware for GitLab).
- Propagate the same result/exception to all waiters on a key.
- Module-level singleton lives on the flattened module; package copy has its own if imported separately.

## ANTI-PATTERNS
- NO unbounded waiter lists.
- NO swallowing exceptions without propagating to all waiters.
- NO importing both package and flattened paths (dual singletons).
- NO treating `coalescing/service.py` as a thin re-export — it is a full copy.
