# AGENTS.md - Domain/Interfaces

Cross-cutting ports and Protocols (469 lines).

## STRUCTURE
```
prdiffer/domain/interfaces/
├── vcs_provider.py          # VCSDiffRepositoryInterface
├── pr_diff_reader.py        # SessionPRDiffReader, PRDiffSnapshot, session port
├── protocols.py             # Application component Protocols
├── input_validation.py      # InputValidatorProtocol
├── request_coalescing.py    # Request coalescing port
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

## CONVENTIONS
- Prefer `Protocol` / ABC with explicit method signatures.
- Keep application-agnostic except where MCP orchestration needs a stable port.

## ANTI-PATTERNS
- NO implementations in this package.
- NO FastMCP / framework types.
