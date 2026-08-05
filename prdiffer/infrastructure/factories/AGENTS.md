# AGENTS.md - Infrastructure/Factories

InfrastructureFactory implements domain factory interface (179 lines).

## STRUCTURE
```
prdiffer/infrastructure/factories/
├── infrastructure_factory.py  # create_* for all infra services
└── __init__.py
```

## METHODS (HIGH LEVEL)
Settings, logger, cache, repository cache, GitHub API, diff, pattern matching, retry, PR diff service, file processor, diff generator, input validator.

## CONVENTIONS
- Return domain interfaces / concrete adapters as appropriate for callers.
- `get_infrastructure_factory()` for process-wide access.

## ANTI-PATTERNS
- NO circular imports with application layer (application should inject, not re-enter carelessly).
