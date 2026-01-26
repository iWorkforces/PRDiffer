# AGENTS.md - Infrastructure Layer

External integrations: GitHub API, caching, logging, utilities, VCS providers, DI container.

## OVERVIEW
Implements domain interfaces, handles I/O/network, provides VCS providers, manages dependencies.

## STRUCTURE
```
prdiffer/infrastructure/
├── github/              # GitHub API client
├── vcs_providers/       # Multi-provider VCS abstraction
├── utils/               # Utilities (retry, circuit breaker, diff)
├── logging/             # Logging infrastructure
├── security/            # Input validation
├── factories/           # Infrastructure factories
├── services/            # Infrastructure services
├── di_container.py      # ServiceContainer DI
├── service_factory.py   # ServiceFactory
└── *Repository.py       # Repository implementations
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add GitHub integration** | `github/`, `*_repository.py` | Use PyGithub |
| **Add VCS provider** | `vcs_providers/` | Implement VCSDiffRepositoryInterface |
| **Add DI service** | `di_container.py`, `service_factory.py` | Register singleton/transient |
| **Add utility** | `utils/` | Pure functions preferred |

## CONVENTIONS

### Dependency Injection
- Constructor injection with `container=None` fallback
- ServiceContainer for singletons, ServiceFactory for creation
- Backward compatible with singletons

### Error Handling
- RetryHandler with exponential backoff
- CircuitBreaker for failure thresholds
- APIHealthTracker for monitoring

### Caching
- MD5 hash keys
- Commit-based invalidation
- TTL support

## ANTI-PATTERNS

- **NO direct PyGithub in application** → Use infrastructure services
- **NO blocking I/O mixed with async** → Use AsyncParallelExecutor
- **NO empty catch blocks** → Always log
