# Changelog

All notable changes to PRDifferMCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.2] - 2026-08-06

### Added
- GitLab support for MCP tools `approve_pr` and `describe_pr` (alongside existing `get_pr_diff`)
- `GitLabPROperationsProtocol` and note-then-approve MR mutation path via `GitLabRuntime`
- Agent skill dual-provider docs (`skills/prdiffer/SKILL.md`)
- Unit coverage for GitLab MR ops, ToolRegistry provider dispatch, and factory ops auto-wire

### Changed
- `approve_pr` / `describe_pr` route via `parse_pr_target` (GitHub PR + GitLab MR URLs)
- Tool failure metrics use the real tool name; empty/whitespace body rejected at the tool boundary
- Package version synchronized in `pyproject.toml` and `prdiffer/version.py`

## [0.5.0] - 2026-01-30

### Added
- **LazyLoggerMixin**: New shared utility for lazy logger initialization (`prdiffer/infrastructure/utils/logger_factory.py`)
- **InjectionDetector**: Extracted pattern-based threat detection (`prdiffer/infrastructure/security/injection_detector.py`)
- **Sanitizer**: Extracted input sanitization logic (`prdiffer/infrastructure/security/sanitizer.py`)
- **ToolRegistry**: Extracted MCP tool registration from mcp_server (`prdiffer/application/tool_registry.py`)
- **WebhookHandler**: Extracted GitHub webhook processing (`prdiffer/application/webhook_handler.py`)
- **HealthEndpoints**: Extracted health checks and metrics (`prdiffer/application/health_endpoints.py`)
- **Error Code System**: Standardized error codes (E1xxx-E5xxx) for 67% of exceptions (42/62)
- Enhanced test coverage with 32 new test files

### Changed
- **Refactored mcp_server.py**: Reduced from 886 to 239 lines (73% reduction)
- **Refactored input_validator.py**: Reduced from 772 to 571 lines (26% reduction)
- **Refactored retry_handler.py**: Removed duplicate logger code, now uses LazyLoggerMixin
- **Refactored diff_utils.py**: Removed duplicate logger code, now uses LazyLoggerMixin
- Converted 11 files to use structured error codes (E-code format)
- Improved code modularity with focused, single-responsibility modules

### Fixed
- Eliminated 24+ lines of duplicate logger initialization code
- Standardized error handling across application, infrastructure, and domain layers

### Technical Debt
- Replaced all threading locks with async primitives (anyio.Lock)
- Analyzed and documented low-priority TODOs (intentional future features)
- Improved Clean Architecture layer separation

### Quality
- All linting checks passing (0 errors)
- All type checks passing (0 errors)
- 1,212 tests passing
- 100% backward compatible (no breaking changes)

### Documentation
- Updated AGENTS.md knowledge base
- Created comprehensive Sprint 3 completion reports
- Added release notes and changes summary

## [0.4.9] - 2026-01-29

### Added
- Authentication system improvements
- Centralized PR URL parsing

### Changed
- Improved authentication component
- Enhanced PR URL validation

## [0.4.7] - 2026-01-20

### Added
- Initial release features
- GitHub PR diff analysis
- Full-file context diffs
- Commit message integration
- Intelligent file filtering
- Smart caching with commit-based invalidation
- Security features (input validation, rate limiting, authentication)
- Multiple transport modes (stdio, HTTP, SSE, streamable-HTTP)
- Async architecture with anyio
- Clean Architecture implementation

### Infrastructure
- FastMCP framework integration
- PyGithub API client
- Dynaconf configuration management
- Prometheus metrics support
- GitHub webhook support

---

## Legend

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features that will be removed in future versions
- **Removed**: Features that have been removed
- **Fixed**: Bug fixes
- **Security**: Security improvements
- **Technical Debt**: Code quality and maintainability improvements

## Version History

- **0.5.0** - Sprint 3: Code Quality & Technical Debt Reduction
- **0.4.9** - Authentication and URL parsing improvements
- **0.4.7** - Initial stable release

[0.5.0]: https://github.com/yourusername/PRDifferMCP/compare/v0.4.9...v0.5.0
[0.4.9]: https://github.com/yourusername/PRDifferMCP/compare/v0.4.7...v0.4.9
[0.4.7]: https://github.com/yourusername/PRDifferMCP/releases/tag/v0.4.7
