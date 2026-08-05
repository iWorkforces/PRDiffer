# AGENTS.md - Domain Unit Tests

Pure domain tests without I/O (~5.2K lines across subpackages).

## STRUCTURE
```
tests/unit/domain/
├── entities/                      # Rich/anemic entity tests
├── usecases/                      # Use case orchestration + purity
├── services/                      # Interface contracts
├── interfaces/                    # Protocol tests
├── config/                        # GitHubConfig
├── factories/                     # Factory interface tests
├── test_error_codes.py
├── test_errors.py
├── test_exceptions.py
├── test_vcs_provider_interface.py
└── test_vcs_provider_registry.py  # 601
```

## CONVENTIONS
- No network, no filesystem, no Dynaconf.
- Assert business methods on `FilePatchInfo` thoroughly.
- Keep use case tests on mocked ports.

## ANTI-PATTERNS
- NO importing infrastructure from domain tests except when testing pure re-exports (prefer none).
