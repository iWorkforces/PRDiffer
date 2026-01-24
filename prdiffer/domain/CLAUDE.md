# CLAUDE.md - Domain Layer

This file provides guidance for working with the Domain Layer of PRDiffer.

**Current Version:** 0.4.8

## Domain Layer Overview

The domain layer contains the core business logic and entities, following Domain-Driven Design principles. It has no dependencies on external frameworks or infrastructure.

## Key Components

### Entities (`entities/`)

**FilePatchInfo** (`file_patch.py`)
- Core dataclass representing file changes in a PR
- Contains both file content (`base_file`, `head_file`) and metadata
- Key fields:
  - `patch`: Unified diff string
  - `filename`: File path in repository
  - `edit_type`: EDIT_TYPE enum (ADDED, DELETED, MODIFIED, RENAMED, UNKNOWN)
  - `num_plus_lines`/`num_minus_lines`: Change statistics
  - `language`: Optional programming language detection
  - `ai_file_summary`: Optional AI-generated summary

**PRDiff Models** (`pr_diff.py`)
- `PRDiff`: Pydantic model for PR information with commit messages and diff content
- Uses Pydantic for validation and serialization

### Repository Interfaces (`repositories/`)

**PRDiffRepositoryInterface** (`pr_diff_repository.py`)
- Abstract interface defining the contract for PR diff data retrieval
- Properties: `repo_owner`, `repo_name`, `pr_number`
- Methods: `async get_pr_diff()`, `get_latest_commit_sha()`
- Implemented by infrastructure layer (GitHubPRDiffRepository)

### Use Cases (`usecases/`)

**GetPRDiffUseCase**
- Simple orchestrator that delegates to repository and cache service
- Follows single responsibility principle
- Provides abstraction layer between application and infrastructure
- Accepts dependencies via constructor injection (Repository + CacheService)
- Supports optional caching with commit-based invalidation

### Service Interfaces (`services/`)

Abstract interfaces for domain services. See `services/CLAUDE.md` for detailed documentation.

**Key Interfaces:**
- `CacheServiceInterface` - Caching operations
- `LoggerServiceInterface` - Structured logging
- `SettingsServiceInterface` - Configuration management
- `GitHubAPIServiceInterface` - GitHub API operations
- `PRDiffServiceInterface` - PR diff operations
- `RetryServiceInterface` - Retry logic
- `PatternMatchingServiceInterface` - File pattern matching
- `DiffServiceInterface` - Diff generation
- `RepositoryCacheServiceInterface` - Repository instance caching

### Factory Interfaces (`factories/`)

Abstract factory interfaces for creating infrastructure services while maintaining dependency inversion.

**InfrastructureFactoryInterface** (`infrastructure_factory.py`)
- Provides methods to create all infrastructure services
- Enables application layer to obtain service instances without coupling to implementations
- Creates core services (cache, logger, settings)
- Creates GitHub integration services (API client, diff service, pattern matcher)
- Creates application components (URL validator, rate limiter, metrics tracker)

**Implementation:** `InfrastructureFactory` in `infrastructure/factories/`

### Error Handling (`errors.py`, `exceptions.py`)

The domain layer provides comprehensive error handling with structured error codes and exception hierarchy.

**Error Codes** (`errors.py`):
- **15 standardized error codes** across 5 categories (E1xxx-E5xxx)
- **ErrorCode dataclass**: code, name, message, remediation, category
- Categories:
  - E1xxx: Input validation (E1001-E1006)
  - E2xxx: Authentication/authorization (E2001-E2003)
  - E3xxx: Rate limiting (E3001-E3003)
  - E4xxx: Resource not found (E4001-E4004)
  - E5xxx: Internal server (E5001-E5005)

**Exception Hierarchy** (`exceptions.py`):
- **27 exception types** organized into 9 categories
- **Base**: `PRDifferException` with message and details
- Categories:
  - Authentication (6): AuthenticationError, InvalidTokenError, ExpiredTokenError, MissingTokenError, AuthorizationError, InsufficientPermissionsError
  - Rate Limiting (3): RateLimitError, GlobalRateLimitError, UserRateLimitError
  - Validation (5): ValidationError, InvalidURLError, InvalidRepositoryError, InvalidPRNumberError, UnsupportedFormatError
  - GitHub API (7): GitHubAPIError, RepositoryNotFoundError, PRNotFoundError, FileNotFoundError, GitHubAuthenticationError, GitHubConnectionError, GitHubRateLimitError
  - Cache (3): CacheError, CacheInvalidationError, CacheCorruptionError
  - Configuration (4): ConfigurationError, MissingConfigurationError, InvalidConfigurationError, SecretsError
  - Processing (4): ProcessingError, DiffGenerationError, FileProcessingError, PatternMatchingError
  - Resource (4): ResourceError, ResourceExhaustedError, MemoryLimitError, TimeoutError
  - Security (4): SecurityError, SuspiciousOperationError, InputSanitizationError, SignatureVerificationError

### Configuration (`config/`)

The domain layer provides frozen configuration objects for type-safe settings management.

**GitHubConfig** (`github_config.py`):
- **Frozen dataclass** with 20+ configuration fields
- **Configuration Groups**:
  - Basic API Settings: rate_limit, timeout, max_retries, retry_delay
  - Smart Retry: retry_on_404 (false), retry_on_403 (true), retry_on_500 (true)
  - Circuit Breaker & Adaptive Retry: circuit_breaker_enabled, failure_threshold, timeout, adaptive_retry_enabled, max_adaptive_delay
  - File Filtering: ignore_patterns (tuple), valid_extensions (tuple) - 60+ file types
  - Parallel Diff Processing: diff_parallel_enabled, diff_parallel_threshold (3), diff_max_workers (4), diff_worker_timeout (30.0)
  - File Processing Limits: max_files_allowed (50), large_file_threshold, chunk_size, max_diff_size
- **Methods**:
  - `from_dict(config)`: Factory method for dict-to-instance
  - `to_dict()`: Instance-to-dict conversion
  - `with_overrides(**kwargs)`: Config cloning with overrides
  - `should_ignore_file(filename)`: fnmatch pattern matching
  - `has_valid_extension(filename)`: Extension validation
  - `should_process_file(filename)`: Combined validation

**Constants** (`constants.py`):
- **Limits**: URL/input validation, GitHub API, cache, request coalescing, file processing, circuit breaker, parallel processing
- **Thresholds**: File change thresholds (SIGNIFICANT_CHANGES, LARGE_CHANGES), retry thresholds, lockout duration
- **Defaults**: MCP server, authentication, cache, logging, token validation
- **Timeouts**: API and request timeouts
- **RegularExpressions**: GitHub URL patterns, command injection, path traversal, SQL injection, Git ref validation

## Development Guidelines

### When Modifying Entities
- Keep entities pure - no external dependencies
- Use dataclasses for simple data structures (FilePatchInfo)
- Use Pydantic models for validation/serialization (PRDiff)
- Add new EDIT_TYPE values as needed for different change types

### When Adding Use Cases
- Follow the dependency inversion principle
- Accept repository interfaces, not concrete implementations
- Keep business logic in use cases, not in entities or repositories
- Use async/await for I/O operations

### Data Flow Pattern
1. **Application Layer** → calls use case
2. **Use Case** → calls repository interface
3. **Infrastructure Repository** → implements interface, returns domain entities
4. **Domain Entities** → pure business objects with no external dependencies

## File Change Processing

The `FilePatchInfo` entity represents the complete context of a file change:
- **Content**: Full file content before (`base_file`) and after (`head_file`) changes
- **Diff**: Unified diff format in `patch` field
- **Metadata**: Change type, statistics, language detection
- **Extended Info**: Optional AI summaries and analysis

This rich representation enables detailed diff analysis and supports various output formats in the application layer.

## Related Documentation

- **Infrastructure Layer**: `../infrastructure/CLAUDE.md` - Infrastructure implementations of domain interfaces
- **Application Layer**: `../application/CLAUDE.md` - Application orchestration and MCP server
- **Service Interfaces**: `services/CLAUDE.md` - Detailed service interface documentation
- **Factory Interfaces**: `factories/CLAUDE.md` - Factory interface documentation
- **Entity Documentation**: `entities/CLAUDE.md` - Core business entities
- **Use Case Documentation**: `usecases/CLAUDE.md` - Business logic orchestration
- **Main Package**: `../CLAUDE.md` - Overall architecture and package structure
- **Testing**: `tests/unit/domain/CLAUDE.md` - Domain layer testing guide
