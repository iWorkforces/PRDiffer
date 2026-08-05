# AGENTS.md - Domain/Interfaces

Cross-cutting ports and Protocols (~520 lines). Package 0.6.0.

## STRUCTURE
```
prdiffer/domain/interfaces/
├── vcs_provider.py          # VCSDiffRepositoryInterface (~112)
├── pr_diff_reader.py        # SessionPRDiffReader, PRDiffSnapshot, session port (~57)
├── protocols.py             # Application component Protocols (~180)
├── input_validation.py      # InputValidatorProtocol (~121)
├── request_coalescing.py    # RequestCoalescingProtocol (~50)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **New VCS capability** | `vcs_provider.py` | Extend ABC; implement in infrastructure |
| **GitHub session path** | `pr_diff_reader.py` | `SessionPRDiffReader.open_pr_diff_session` |
| **Component typing** | `protocols.py` | Auth, rate limit, metrics, health, config, PR ops |
| **Security port** | `input_validation.py` | Injected into auth / tools |
| **Coalescing port** | `request_coalescing.py` | Deduplicate concurrent PR fetches |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `VCSDiffRepositoryInterface` | ABC | `vcs_provider.py` | Multi-provider get_pr_diff / supports_repository |
| `PRDiffSnapshot` | Frozen dataclass | `pr_diff_reader.py` | owner/repo/pr + base/head SHA + file count |
| `PRDiffReadSessionInterface` | Protocol | `pr_diff_reader.py` | snapshot, `build_pr_diff`, `aclose` |
| `SessionPRDiffReader` | Protocol | `pr_diff_reader.py` | Extends use-case `PRDiffReader` + open session |
| `InputValidatorProtocol` | Protocol | `input_validation.py` | URL/path/token/sanitize contracts |
| `RequestCoalescingProtocol` | Protocol | `request_coalescing.py` | `coalesce` / clear / stats |
| `RateLimiterProtocol` | Protocol | `protocols.py` | Rate limit checks |
| `MetricsTrackerProtocol` | Protocol | `protocols.py` | Request metrics |
| `PROperationHandlerProtocol` | Protocol | `protocols.py` | High-level PR ops |
| `HealthMonitorProtocol` | Protocol | `protocols.py` | Health status |
| `ServerConfigurationProtocol` | Protocol | `protocols.py` | Transport/server config |
| `AuthenticationProtocol` | Protocol | `protocols.py` | Auth + client id extraction |

## SESSION PATH (full-diff v2)
- GitHub implements `SessionPRDiffReader`: one `open_pr_diff_session` → snapshot (incl. `head_sha`) → cache key → `build_pr_diff` → always `aclose` in `finally`.
- Non-session readers (e.g. GitLab) keep legacy `PRDiffReader` methods defined in `usecases/pr_diff_usecases.py` (`get_pr_diff`, `get_latest_commit_sha`).
- `GetPRDiffUseCase` selects path via structural check for `open_pr_diff_session` on the concrete type (not instance attrs).

## CONVENTIONS
- Prefer `Protocol` / ABC with explicit method signatures.
- Keep application-agnostic except where MCP orchestration needs a stable port (`protocols.py`).
- Session ports return domain entities (`PRDiff`), never SDK models.

## ANTI-PATTERNS
- NO implementations in this package.
- NO FastMCP / framework types.
- NO skipping `aclose` on open sessions.
- NO putting session logic only on infrastructure without this domain contract.
