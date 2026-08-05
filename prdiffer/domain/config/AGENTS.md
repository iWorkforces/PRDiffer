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
| **GitHub settings model** | `github_config.py` | Frozen; tuple fields for hashability |
| **Config interface** | `github_config_interface.py` | Implemented by infrastructure SettingsService |

## CONVENTIONS
- Immutable config objects only.
- Infrastructure loads Dynaconf and maps into these domain types.
- Never read env/files from this package.

## ANTI-PATTERNS
- NO Dynaconf/os.environ here.
- NO mutable config bags shared across threads without care.
