# AGENTS.md - Domain/Config

Configuration value objects and interfaces (no I/O). Package 0.6.0.

## STRUCTURE
```
prdiffer/domain/config/
├── github_config.py            # GitHubConfig frozen dataclass (~266)
├── github_config_interface.py  # GitHubConfigDict + GitHubConfigInterface Protocol (~108)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **GitHub settings model** | `github_config.py` | Frozen; tuple fields for hashability; full-diff limits + parallel flags |
| **Config interface** | `github_config_interface.py` | `@runtime_checkable` Protocol + TypedDict for DI |
| **Defaults** | `github_config.py` top | Match `settings.toml` / plan contracts |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `GitHubConfig` | Frozen dataclass | `github_config.py` | Central GitHub settings VO |
| `GitHubConfigInterface` | Protocol | `github_config_interface.py` | DI / typing surface |
| `GitHubConfigDict` | TypedDict | `github_config_interface.py` | `from_dict` / `with_overrides` keys |
| `github_worker_capacity` | property | `GitHubConfig` | 1 when `parallel_file_fetch_enabled` is false |

## FULL-DIFF FIELDS
| Field | Default | Notes |
|-------|---------|-------|
| `timeout` | 30 | Provider/GitHub SDK timeout (seconds) |
| `pr_diff_request_timeout_seconds` | 180.0 | Absolute request/coalescing deadline; must be `> timeout` |
| `max_file_size_bytes` | 10_485_760 (10 MiB) | Content size admission |
| `max_total_chars` | 200_000 | Aggregate public diff char budget |
| `max_files_allowed` | 50 | Selected-file admission limit |
| `parallel_file_fetch_enabled` | `false` | Opt-in; capacity is 1 when off |
| `parallel_head_base_fetch_enabled` | `false` | Opt-in concurrency |
| `parallel_diff_generation_enabled` | `false` | Opt-in concurrency |
| `max_concurrent` | 4 | Worker cap when parallel fetch enabled |

Also: retry/circuit-breaker knobs, `ignore_patterns` / `valid_extensions` as tuples, legacy `diff_parallel_*` for older parallel-diff paths.

## CONVENTIONS
- Immutable config objects only; `__post_init__` validates positives and `timeout < pr_diff_request_timeout_seconds`.
- Infrastructure loads Dynaconf and maps into these domain types (`from_dict` / `to_dict`).
- Never read env/files from this package.
- Helpers: `should_ignore_file`, `has_valid_extension`, `should_process_file`, `with_overrides`.

## ANTI-PATTERNS
- NO Dynaconf / `os.environ` here.
- NO silent coercion of zero/negative limits (`ConfigurationError` on invalid).
- NO mutable config bags shared across threads without care.
- NO defaulting full-diff parallel flags to `true` without an explicit opt-in decision.
