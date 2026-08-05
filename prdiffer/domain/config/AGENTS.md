# AGENTS.md - Domain/Config

Configuration value objects and interfaces (no I/O).

## STRUCTURE
```
prdiffer/domain/config/
├── github_config.py            # GitHubConfig frozen dataclass
├── github_config_interface.py  # Settings/config port
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **GitHub settings model** | `github_config.py` | Frozen; tuple fields for hashability; full-diff limits + parallel flags |
| **Config interface** | `github_config_interface.py` | Protocol + TypedDict for DI |

## FULL-DIFF FIELDS
| Field | Default | Notes |
|-------|---------|-------|
| `timeout` | 30 | Provider/GitHub SDK timeout (seconds) |
| `pr_diff_request_timeout_seconds` | 180 | Absolute request/coalescing deadline; must be `> timeout` |
| `max_file_size_bytes` | 10 MiB | Content size admission |
| `max_total_chars` | 200000 | Aggregate public diff char budget |
| `parallel_*_enabled` | `false` | Opt-in; capacity is 1 when fetch parallel is off |
| `max_files_allowed` | 50 | Selected-file admission limit |

## CONVENTIONS
- Immutable config objects only; `__post_init__` validates positives and timeout ordering.
- Infrastructure loads Dynaconf and maps into these domain types.
- Never read env/files from this package.

## ANTI-PATTERNS
- NO Dynaconf/os.environ here.
- NO silent coercion of zero/negative limits.
- NO mutable config bags shared across threads without care.
