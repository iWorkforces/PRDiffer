# CLAUDE.md - Infrastructure Layer

This file provides guidance for working with the Infrastructure Layer of CCPRAgents.

## Infrastructure Layer Overview

The infrastructure layer contains external integrations, data access implementations, and cross-cutting concerns like settings and logging. This layer implements interfaces defined in the domain layer.

## Key Components

### GitHub Integration (`github_repository.py`)

**GitHubPRDiffRepository**
- Implements `PRDiffRepository` interface from domain layer
- Uses PyGithub library for GitHub API integration
- Handles authentication, rate limiting, and API error handling

**Critical Implementation Details:**

**Caching Architecture:**
- Settings service uses manual caching instead of `@lru_cache` 
- Reason: Dynaconf objects are not hashable, causing `TypeError: unhashable type: 'list'`
- Solution: Manual cache variables with list-to-tuple conversion for hashability

**Full-File Diff Generation:**
- `_build_full_file_patch()`: Creates complete file context diffs (not minimal hunks)
- Method signature: Instance method (not static) for proper `self._build_full_file_patch()` calls
- Uses `difflib.SequenceMatcher` for accurate line-by-line comparison
- Output format: `@@ -1,134 +1,139 @@` style headers with full file context

**File Content Processing Pipeline:**
1. **File Retrieval**: `_get_files()` via PyGithub API
2. **File Filtering**: `_filter_files()` based on `ignore_patterns`/`valid_extensions` settings
3. **Content Loading**: `_get_pr_file_content()` for base/head commits (limited by `max_files_allowed`)
4. **Patch Generation**: `_extend_patch()` creates full-file unified diffs
5. **Extended Diff**: `_pr_generate_extended_diff()` formats with headers and context

**GitHub API Strategies:**
- **Authentication**: Settings → parameters → `GITHUB_TOKEN` env variable fallback
- **Merge Base Handling**: Uses `repo.compare()` to find proper base commit (handles parallel merges)
- **Rate Limiting**: Configurable limits with graceful degradation
- **Content Encoding**: Multiple encoding attempts (UTF-8, iso-8859-1, latin-1, ascii, utf-16)

### Settings Management (`settings.py`)

**SettingsService**
- Uses Dynaconf for TOML configuration with environment overrides
- Implements manual caching to avoid `@lru_cache` hashability issues
- Converts lists to tuples for hashable cache keys

**Key Methods:**
- `get()`: Manual caching with hashable key conversion
- `get_github_settings()`: Returns tuple-converted lists for `ignore_patterns`/`valid_extensions`
- `clear_cache()`: Manual cache clearing

**Configuration Structure:**
- `[default]`, `[development]`, `[production]`, `[testing]` environments
- GitHub, MCP, cache, and application settings sections
- File filtering patterns and extensions

### Logging System (`logging/`)

**Architecture:**
- **Domain Service**: `LoggerService` abstract interface in domain layer
- **Infrastructure Implementation**: `ConsoleLogger` in infrastructure layer
- **Global Access**: `get_logger()` singleton pattern

**ConsoleLogger Features:**
- ANSI color-coded output (DEBUG=Cyan, INFO=Green, WARNING=Yellow, ERROR=Red, CRITICAL=Magenta)
- Structured logging with context data via `**kwargs`
- Log level filtering based on settings
- Timestamp formatting and stderr routing for errors

## Development Guidelines

### Working with GitHub API
- Always handle `Exception` gracefully (return empty strings rather than failing)
- Use merge base commits for accurate diff comparison
- Implement file content loading limits to avoid rate limiting
- Test with both authenticated and anonymous access

### Settings Management
- Never use `@lru_cache` on methods with `self` parameter containing Dynaconf
- Convert lists to tuples when storing in cache keys
- Use environment-specific settings for different deployment contexts
- Clear cache when settings change

### Logging Best Practices
- Use structured logging with context: `logger.info("message", key=value)`
- Check log levels in performance-critical paths
- Route errors/critical to stderr, info/debug to stdout
- Include relevant request context in log messages

### File Processing Optimization
- Implement file filtering early to reduce API calls
- Use full-file context for better diff analysis
- Handle binary files and encoding errors gracefully
- Respect GitHub API rate limits with proper error handling

## Critical Technical Issues Resolved

### Serialization Problem (`TypeError: unhashable type: 'list'`)
**Root Cause:** `@lru_cache` tried to hash `SettingsService` instance containing unhashable Dynaconf objects
**Solution:** Replaced with manual caching using instance variables

### Method Signature Bug (`_build_full_file_patch`)
**Root Cause:** Method defined as static but called as instance method
**Solution:** Changed to instance method: `def _build_full_file_patch(self, ...):`

### Output Formatting Issue
**Root Cause:** Missing blank line after file headers in diff output
**Solution:** Added extra `\n` in format string: `f"\n\n## File: '{filename}'\n\n{patch}"`

## External Dependencies

- **PyGithub**: GitHub API client library
- **Dynaconf**: Configuration management with TOML support  
- **python-dotenv**: Environment variable loading
- **Standard Library**: `difflib`, `re`, `logging`, `datetime`

This infrastructure layer provides robust external integrations while maintaining clean separation from domain logic through well-defined interfaces.