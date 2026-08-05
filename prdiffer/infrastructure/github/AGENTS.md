# AGENTS.md - Infrastructure/GitHub

PyGithub-backed API client, file processing, and diff generation (~1.6K lines).

## STRUCTURE
```
prdiffer/infrastructure/github/
├── client.py                # GitHub API client facade (276)
├── client_operations.py     # Operations mixins/helpers (331)
├── client_models.py         # Client-side models (16)
├── file_processor.py        # File fetch/filter/chunk (437)
├── diff_generator.py        # Unified diff generation (326)
├── etag_adapter.py          # Conditional requests / 304 (121)
├── mappers.py               # API → domain mapping (88)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **API calls** | `client.py`, `client_operations.py` | Retry/CB integration points |
| **File handling** | `file_processor.py` | Filters, limits, parallel fetch |
| **Diff build** | `diff_generator.py` | `generate_ordered_file_diffs` → `GeneratedFileDiff` (full-context, ordered) |
| **Bandwidth** | `etag_adapter.py` | ETag / 304 |
| **Domain map** | `mappers.py` | To FilePatchInfo / responses |
| **Inventory admission** | `inventory.py` | Authoritative `changed_files` vs enumeration; selected N+1 → E5020 |
| **Request session** | `pr_diff_session.py` | anyio `to_thread` + CapacityLimiter; one metadata lookup per request |

## CONVENTIONS
- Never return raw PyGithub objects past this package boundary.
- Respect rate limits (403/429) via retry utilities.
- Honor file ignore patterns / extension allowlists from settings.
- **Typed content**: `get_file_content` / batch APIs return `FileContentAvailable | FileContentUnavailable`.
  - Empty text is available (`text == ""`).
  - Cache key is `(repo_full_name, path, immutable_ref)`; only available text is cached.
  - Auth/rate-limit/transport/retry-exhausted failures raise operational exceptions — never become unavailable union values.

## ANTI-PATTERNS
- NO domain imports of `github.*` SDK.
- NO unbounded file downloads without limits.
- NO caching unavailable sentinels or empty-string error stand-ins.
