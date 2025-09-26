# CLAUDE.md - Domain Layer

This file provides guidance for working with the Domain Layer of CCPRAgents.

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
