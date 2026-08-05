# AGENTS.md - GitHub Infrastructure Unit Tests

12 files, ~3.3K lines. Core full-diff pipeline coverage.

## STRUCTURE
```
tests/unit/infrastructure/github/
├── test_api_client.py                     # ~131
├── test_api_client_comprehensive.py       # ~519
├── test_file_content_typed.py             # ~113 — FileContentAvailable / Unavailable
├── test_file_processor.py                 # ~208
├── test_file_processor_comprehensive.py   # ~567
├── test_file_processor_ordered.py         # ~112 — ordered strict assembly
├── test_diff_generator.py                 # ~101
├── test_diff_generator_comprehensive.py   # ~738
├── test_generated_file_diffs.py           # ~180 — ordered full-context generation
├── test_github_mappers.py                 # ~417
├── test_inventory_admission.py            # ~91 — authoritative inventory + admission
└── test_pr_diff_session.py                # ~99 — session isolation / cache_identity / CapacityLimiter
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| **Typed file content** | `test_file_content_typed.py` | Zero-byte, decode failures, cacheability |
| **Inventory / 3000 cap** | `test_inventory_admission.py` | `INVENTORY_TRUNCATED`, admission selection |
| **Ordered processor** | `test_file_processor_ordered.py` | Strict assembly, sync/async parity |
| **Generated full-context diffs** | `test_generated_file_diffs.py` | Ordered diffs, E5003 mapping |
| **PR diff session** | `test_pr_diff_session.py` | anyio limiter, aclose, GitHub v2 `cache_identity` |
| **Happy vs edge** | `*_comprehensive.py` | Edge/error branches |

## CONVENTIONS
- Basic vs comprehensive split: happy path vs edge/error branches.
- Mock `github.Github` hierarchy; assert our wrapper behavior.
- Full-diff incompleteness must surface as `FullDiffIncompleteError` with a reason (never silent truncation).
- Session tests may use `@pytest.mark.anyio` + anyio primitives.

## ANTI-PATTERNS
- NO real GitHub network.
- NO treating 404 file content as retryable transient errors.
