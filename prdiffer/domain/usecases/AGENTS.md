# AGENTS.md - Domain/Use Cases

Thin business orchestration over injected ports (~258 lines). Package 0.6.0.

## STRUCTURE
```
prdiffer/domain/usecases/
├── pr_diff_usecases.py          # GetPRDiffUseCase + PRDiffReader Protocol (~134)
├── pr_description_usecases.py   # UpdatePRDescriptionUseCase (~62)
├── pr_approval_usecases.py      # ApprovePRUseCase (~62)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Fetch structured diff** | `pr_diff_usecases.py` | Session (GitHub v2) vs legacy (GitLab) paths |
| **Update description** | `pr_description_usecases.py` | Validates then `update_pr_description` |
| **Approve PR** | `pr_approval_usecases.py` | Validates then `approve_pr_with_comment` |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `PRDiffReader` | Protocol | `pr_diff_usecases.py` | `get_pr_diff` + `get_latest_commit_sha` |
| `GetPRDiffUseCase` | Use case | `pr_diff_usecases.py` | Cache + reader orchestration |
| `_is_session_reader` | Helper | `pr_diff_usecases.py` | Type-level session capability check |
| `_execute_session_path` | Method | `pr_diff_usecases.py` (~61–100) | open session → v2 cache → build → aclose |
| `_execute_legacy_path` | Method | `pr_diff_usecases.py` (~102–134) | SHA → cache → get_pr_diff |
| `UpdatePRDescriptionUseCase` | Use case | `pr_description_usecases.py` | Description update |
| `ApprovePRUseCase` | Use case | `pr_approval_usecases.py` | Approve + compliment |

## SESSION VS LEGACY (GetPRDiffUseCase)
1. **Session path** (GitHub full-diff v2): if reader type has `open_pr_diff_session`:
   - Open session; use `snapshot.head_sha`
   - Cache key: `github_full_diff_v2_key(owner, repo, pr, head_sha)` (+ optional namespace)
   - Read via `unwrap_pr_diff_cache_value` (ignore unversioned/v1/wrong-schema)
   - On miss: `session.build_pr_diff()`, store under v2 key, always `session.aclose()`
2. **Legacy path** (e.g. GitLab): `get_latest_commit_sha` → cache get/set → `get_pr_diff`
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
- NO writing unversioned cache payloads under `github-full-diff-v2` keys without schema discipline.
