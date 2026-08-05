# AGENTS.md - Domain/Factories

Abstract factory contracts for dependency inversion (134 lines).

## STRUCTURE
```
prdiffer/domain/factories/
├── application_factory.py      # ApplicationFactoryInterface (68)
├── infrastructure_factory.py   # InfrastructureFactoryInterface (65)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **App component factory port** | `application_factory.py` | Rate limiter, metrics, auth, health, … |
| **Infra service factory port** | `infrastructure_factory.py` | Cache, GitHub API, retry, validator, … |

## CONVENTIONS
- Methods return interfaces/Protocols, not concrete classes.
- Implementations live in `application/factories/` and `infrastructure/factories/`.

## ANTI-PATTERNS
- NO concrete infrastructure imports in domain factories.
- NO service construction with side effects here.
