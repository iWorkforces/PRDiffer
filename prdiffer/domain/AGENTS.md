# AGENTS.md - Domain Layer

Pure business logic layer. No external dependencies, frameworks, or I/O operations.

## OVERVIEW
Core business models, service interfaces, data contracts, and VCS provider registry.

## STRUCTURE
```
prdiffer/domain/
├── entities/           # Core business objects (PRDiff, FilePatchInfo)
├── services/          # Business logic interfaces
├── repositories/       # Data access contracts
├── interfaces/         # Protocol definitions
├── exceptions.py       # Custom exception hierarchy
├── errors.py          # Structured error codes
└── vcs_provider_registry.py  # VCS provider auto-detection
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add business model** | `entities/` | Use Pydantic BaseModel |
| **Add service interface** | `services/` | Abstract methods only |
| **Add VCS provider** | `vcs_provider_registry.py`, `infrastructure/vcs_providers/` | Register provider |

## CONVENTIONS

### Entities
- Use Pydantic BaseModel for validation
- Immutable data models with Field descriptions
- Property methods for derived state

### Service Interfaces
- ABC with @abstractmethod
- No implementation in domain
- Type hints required

### VCS Provider Registry
- Auto-detect from URL patterns
- Register providers with url_pattern
- VCSDiffRepositoryInterface contract

## ANTI-PATTERNS

- **NO external imports** → Keep domain pure
- **NO I/O operations** → Infrastructure only
- **NO framework deps** → Pydantic only
- **NO implementation** → Interfaces/contracts only
