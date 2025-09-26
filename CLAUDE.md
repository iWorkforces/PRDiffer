# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CCPRAgents is an MCP (Model Context Protocol) server that provides GitHub PR diff analysis capabilities. It's built using FastMCP framework and follows Clean Architecture principles with domain-driven design.

## Key Commands

### Environment Setup
```bash
# Install dependencies (requires Python 3.13+)
uv install

# Install development dependencies
uv install --dev
```

### Running the Server
```bash
# Run MCP server (default HTTP transport on port 9101)
uv run python ccpragents/server.py

# Run with different transport/port via environment variables
TRANSPORT=sse PORT=9102 uv run python ccpragents/server.py
```

### Development Commands
```bash
# Lint code (check only)
./start-lint.sh --check

# Lint and auto-fix issues
./start-lint.sh --fix

# Format code
./start-lint.sh --format

# Run complete linting workflow (check, fix, format)
./start-lint.sh --all

# Show linting statistics
./start-lint.sh --stats
```

### Testing
```bash
# Run basic MCP server test
uv run python tests/test_mcp_server.py
```

## Architecture Overview

The codebase follows Clean Architecture with these layers:

### Domain Layer (`ccpragents/domain/`)
- **Entities**: Core business objects
  - `FilePatchInfo`: File change representation with diff and metadata
  - `PRDiff`: PR model with commit messages and diff content
- **Use Cases**: Business logic orchestration
  - `GetPRDiffUseCase`: Fetches and caches PR diff data
- **Repository Interfaces**: Abstract data access contracts
  - `PRDiffRepositoryInterface`: Contract for PR diff retrieval
- **Service Interfaces**: Abstract service contracts
  - `CacheServiceInterface`: Caching abstraction
  - `SettingsServiceInterface`: Configuration abstraction
  - `LoggerServiceInterface`: Logging abstraction
  - `RepositoryCacheServiceInterface`: Repository instance caching

### Infrastructure Layer (`ccpragents/infrastructure/`)

- **GitHub Integration**:
  - `GitHubPRDiffRepository`: PyGithub implementation of `PRDiffRepositoryInterface`
  - **GitHub Components** (`github/`):
    - `api_client`: GitHub API client wrapper
    - `file_processor`: File filtering and validation
    - `diff_generator`: Unified diff generation
    - `parallel_executor`: Concurrent file processing
- **Utility Components** (`utils/`):
  - `retry_handler`: Exponential backoff with jitter
  - `pattern_matcher`: File pattern matching with regex
  - `diff_utils`: Core diff operations
  - `circuit_breaker`: Failure prevention pattern
  - `api_health_tracker`: API performance monitoring
- **Services**:
  - `SettingsService`: Dynaconf-based configuration with manual caching
  - `CacheService`: In-memory commit-based caching
  - `RepositoryCacheService`: Repository instance caching
- **Logging** (`logging/`):
  - `ConsoleLogger`: Structured console output with ANSI colors

### Application Layer (`ccpragents/application/`)

- **MCP Server** (`mcp_server.py`):
  - FastMCP server exposing `get_pr_diff` tool
  - Tool registration and request handling
  - Dependency injection orchestration
- **Components** (`components/`):
  - `URLValidator`: GitHub URL parsing and validation
  - `RateLimiter`: Request rate limiting
  - `MetricsTracker`: Performance metrics collection
  - `PROperationHandler`: PR operations coordination
  - `HealthMonitor`: Server health checks
  - `ServerConfiguration`: Runtime configuration
- **Factory** (`factory.py`):
  - `create_mcp_server`: Component wiring and injection
- **Interfaces** (`interfaces/`):
  - Protocol definitions for component contracts

### Interface Layer

- **Server Entry Point**: `ccpragents/server.py` - main server launcher with dependency initialization

## Key Technical Details

### Settings Configuration

- Uses `settings.toml` with environment-specific overrides (`[development]`, `[production]`, `[testing]`)
- Settings service implements manual caching instead of `@lru_cache` due to Dynaconf object hashability issues
- GitHub settings include file filtering (`ignore_patterns`, `valid_extensions`) stored as tuples for hashability

### PR Diff Processing Pipeline

1. **File Retrieval**: Gets PR files via PyGithub API
2. **File Filtering**: Applies ignore patterns and valid extensions from settings
3. **Content Loading**: Fetches full file content for base and head commits (limited by `max_files_allowed`)
4. **Patch Generation**: Creates full-file unified diffs using `_build_full_file_patch()`
5. **Extended Diff Creation**: Formats output with file headers and full context

### GitHub API Integration

- **Modular Architecture**: Components split into `api_client`, `file_processor`, `diff_generator`, and `parallel_executor`
- **Retry Logic**: Configurable exponential backoff with jitter via `RetryHandler` utility
- **Pattern Matching**: Advanced file filtering using `PatternMatcher` with pre-compiled regex patterns
- **Diff Generation**: Full-file context diffs using `DiffUtils` with multiple encoding support
- **Authentication**: Handles authentication via settings, parameters, or `GITHUB_TOKEN` environment variable
- **Merge Base Handling**: Uses merge base commits for accurate diff comparison (handles parallel merges)
- **Rate Limiting**: Implements rate limiting and timeout configurations with circuit breaker pattern
- **Parallel Processing**: Thread pool execution for concurrent file processing
- **API Health Tracking**: Monitors API performance and error rates
- **Supports both authenticated and anonymous access**

### Transport Configuration

The MCP server supports multiple transport modes configured in `settings.toml`:

- `stdio`: Standard input/output (default for MCP clients)
- `http`: HTTP server mode
- `sse`: Server-sent events
- `streamable-http`: FastMCP streamable HTTP

### Error Handling Patterns

- **Graceful Degradation**: Settings service falls back gracefully when cache keys are unhashable
- **API Error Handling**: GitHub API errors return empty strings rather than failing
- **Retry Strategies**: Configurable exponential backoff with jitter for transient failures
- **Circuit Breaker**: Prevents cascading failures by temporarily disabling failing operations
- **Content Decoding**: File content decoding attempts multiple encodings (UTF-8, iso-8859-1, latin-1, ascii, utf-16)
- **Health Monitoring**: API health tracking to detect and respond to performance degradation

### Caching System

- **Commit-Based Caching**: PR diff data is cached using the latest commit SHA as cache key
- **Automatic Invalidation**: Cache is automatically invalidated when new commits are pushed to the PR
- **Memory Cache**: In-memory caching with commit SHA tracking for freshness
- **Cache Service**: Singleton `CacheService` with commit-based invalidation logic

**Cache Key Structure**: `"owner/repo/pr/number"`
**Cache Data**: `{"commit_sha": str, "data": PRDiff, "timestamp": float}`

**Cache Flow**:

1. On first request: Fetch data from GitHub, cache with current commit SHA
2. On subsequent requests: Check current commit SHA vs cached SHA
3. If SHAs match: Return cached data (cache hit)
4. If SHAs differ: Fetch fresh data and update cache (cache miss)

**MCP Tool Parameter**: `use_cache` (default: `true`) - controls whether caching is used

## Important Implementation Notes

### Modular Architecture
- **Component Extraction**: Original `GitHubPRDiffRepository` (972 lines) refactored into modular components (~200 lines main class)
- **Single Responsibility**: Each component focuses on specific functionality (API client, file processing, diff generation, parallel execution)
- **Interface Compliance**: All components implement domain service interfaces for testability
- **Dependency Injection**: Components use dependency injection for loose coupling

### Caching System
The settings service uses manual caching instead of `@lru_cache` because:
- Dynaconf objects are not hashable
- Lists in configuration are converted to tuples for hashability
- Cache keys handle list-to-tuple conversion in `get()` method

### Full-File Diff Generation
- `_build_full_file_patch()` generates complete file context diffs
- Uses `difflib.SequenceMatcher` for line-by-line comparison
- Method signature fixed from static to instance method for proper `self._build_full_file_patch()` calls
- Output format includes blank line after file header for proper formatting

### File Content Processing
- **Pattern-Based Filtering**: Uses `PatternMatcher` with pre-compiled regex patterns for efficient file validation
- **Batch Processing**: Bulk content retrieval for better API efficiency
- **Parallel Execution**: Thread pool processing for concurrent file operations
- **Content Limiting**: Loads full file content only up to `max_files_allowed` setting (default: 50)
- **Graceful Degradation**: Falls back to patch-only mode for large PRs to avoid rate limiting
- **Encoding Support**: Handles binary files gracefully with multiple encoding attempts (UTF-8, iso-8859-1, latin-1, ascii, utf-16)

### Utility Components
- **RetryHandler**: Configurable exponential backoff with jitter and rate limit detection
- **PatternMatcher**: Efficient file filtering with wildcard support and pre-compiled regex
- **DiffUtils**: Core diff generation with encoding detection and patch extension
- **CircuitBreaker**: Prevents cascading failures by temporarily disabling failing operations
- **APIHealthTracker**: Monitors API performance metrics and error rates