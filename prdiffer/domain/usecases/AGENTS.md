# AGENTS.md - Domain/Use Cases

Thin business orchestration over injected ports. Package 0.6.2.

## STRUCTURE
```
prdiffer/domain/usecases/
├── pr_diff_usecases.py          # GetPRDiffUseCase + PRDiffReader Protocol (~148)
├── pr_description_usecases.py   # UpdatePRDescriptionUseCase (~62)
├── pr_approval_usecases.py      # ApprovePRUseCase (~62)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Fetch structured diff** | `pr_diff_usecases.py` | Session path (GitHub + GitLab) vs legacy two-call path |
| **Update description** | `pr_description_usecases.py` | Validates non-empty body then repository `update_pr_description` (domain path; **MCP tools call repos/ops directly**, not this use case) |
| **Approve PR/MR** | `pr_approval_usecases.py` | Validates non-empty compliment then repository `approve_pr_with_comment` (domain path; **MCP tools call repos/ops directly**, not this use case) |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `PRDiffReader` | Protocol | `pr_diff_usecases.py` | `get_pr_diff` + `get_latest_commit_sha` |
| `GetPRDiffUseCase` | Use case | `pr_diff_usecases.py` | Cache + reader orchestration |
| `_is_session_reader` | Helper | `pr_diff_usecases.py` | Type-level session capability check |
| `_execute_session_path` | Method | `pr_diff_usecases.py` | open → `cache_identity` → build → aclose; optional `base_url` |
| `_execute_legacy_path` | Method | `pr_diff_usecases.py` | SHA → cache → get_pr_diff |
| `UpdatePRDescriptionUseCase` | Use case | `pr_description_usecases.py` | Description update |
| `ApprovePRUseCase` | Use case | `pr_approval_usecases.py` | Approve + compliment |

## SESSION VS LEGACY (GetPRDiffUseCase)
1. **Session path** (GitHub full-diff v2 **and** GitLab full-diff v1): if reader type has `open_pr_diff_session`:
   - Open session (pass `base_url` when the signature accepts it — GitLab custom hosts)
   - Cache via `session.cache_identity` (provider-neutral key + validation token)
   - Read via `unwrap_pr_diff_cache_value` (ignore wrong-schema / legacy keys)
   - On miss: `session.build_pr_diff()`, store under identity key, always `session.aclose()`
2. **Legacy path**: `get_latest_commit_sha` → cache get/set → `get_pr_diff` (non-session readers only)
3. Optional `cache_hit_optimization_enabled` uses `get_optimistic` before authoritative get.

## CONVENTIONS
- Constructor-inject interfaces only (`PRDiffReader` / `CacheServiceInterface` / `PRDiffRepositoryInterface`).
- No framework, auth, or HTTP concerns (those live in application tools).
- Keep use cases short; push provider details to infrastructure.
- Structural session detection inspects the **concrete type** so MagicMock doubles do not take the session path accidentally.

## ANTI-PATTERNS
- NO direct VCS SDK usage.
- NO caching/retry implementation details beyond port calls.
- NO skipping `aclose` on the session path.
- NO writing unversioned cache payloads under strict GitHub-v2 / GitLab-v1 keys without schema discipline.
