# AGENTS.md - PRDifferMCP

Root-level architecture guidance for AI coding assistants.

## Overview

PRDifferMCP is a Python 3.14+ MCP (Model Context Protocol) server that provides GitHub PR diff analysis capabilities. Built with FastMCP framework, follows Clean Architecture principles with domain-driven design.

**Current Version:** 0.4.9

## Architecture Summary

The codebase is organized into three main layers:

### Domain Layer (`prdiffer/domain/`)
- **Entities**: Core business objects (PRDiff, FilePatchInfo)
- **Services**: Business logic interfaces (GitHubAPIServiceInterface, CacheServiceInterface, LoggerServiceInterface, etc.)
- **Repositories**: Data access contracts (PRDiffRepositoryInterface, VCSDiffRepositoryInterface)
- **Interfaces**: Protocol definitions (LoggerServiceInterface, GitHubConfigInterface, etc.)
- **Factories**: Dependency injection abstractions (InfrastructureFactoryInterface)
- **Config**: Configuration models and interfaces (GitHubConfig)
- **Exceptions**: Custom exception hierarchy (PRDifferException with details dict)
- **Errors**: Structured error codes (format: `E{category}{number}_{NAME}`)
- **VCS Provider Registry**: Centralized multi-provider VCS management

### Infrastructure Layer (`prdiffer/infrastructure/`)
- **GitHub Integration**: PyGithub implementation with DI support
- **VCS Providers**: Multi-provider abstraction (GitHub, GitLab, extensible)
- **Services**: SettingsService, CacheService, RepositoryCacheService, RequestCoalescingService, etc.
- **Components**: GitHubAPIClient, FileProcessor, DiffGenerator
- **Utilities**: RetryHandler, PatternMatcher, DiffUtils, CircuitBreaker, APIHealthTracker
- **Factories**: InfrastructureFactory for creating service instances
- **Logging**: ConsoleLogger with ANSI colors
- **Security**: InputValidator for comprehensive input validation
- **DI Infrastructure**: ServiceContainer for dependency injection, ServiceFactory for service creation
- **Async Infrastructure**: AsyncParallelExecutor, RequestCoalescingService with anyio primitives

### Application Layer (`prdiffer/application/`)
- **MCP Server**: FastMCP server implementation with tool registration
- **Components**: AuthenticationMiddleware, RateLimiter, MetricsTracker, HealthMonitor, PROperationHandler, ServerConfiguration
- **Plugin System**: PluginManager for MCP tool plugins with modular architecture
- **Interfaces**: MCP-specific protocols (MCPToolInterface)
- **Factory**: Component wiring and dependency injection

## Key Architectural Features (v0.4.9)

### Multi-Provider VCS System
- VCS provider abstraction with registry pattern
- Auto-detection of provider from repository URLs
- Extensible for adding GitLab, Bitbucket, etc.
- Location: `prdiffer/domain/vcs_provider_registry.py`, `prdiffer/domain/interfaces/vcs_provider.py`

### Dependency Injection Infrastructure
- ServiceContainer: DI container for singleton and transient services
- ServiceFactory: Centralized factory for service creation
- Constructor injection support throughout infrastructure
- Backward compatible with singleton fallbacks

### Plugin System
- MCPToolPlugin interface for modular tool development
- PluginManager for plugin discovery and execution
- get_pr_diff_plugin as first implementation

### Clean Architecture Adherence
- Proper layer separation (Domain → Application → Infrastructure)
- Domain layer has no external dependencies
- Infrastructure layer implements domain interfaces
- Application layer coordinates components
- All classes accept dependencies for easy mocking in tests

## Directory Structure Reference

See individual `AGENTS.md` files in each directory for detailed guidance:
- Root: Overall architecture and project overview (this file)
- `prdiffer/domain/AGENTS.md`: Domain layer entities, services, repositories, interfaces, config, VCS registry
- `prdiffer/infrastructure/AGENTS.md`: Infrastructure components, VCS providers, DI system
- `prdiffer/application/AGENTS.md`: Application components, services, plugin system
- `prdiffer/domain/interfaces/AGENTS.md`: Domain protocol definitions
- `openspec/AGENTS.md`: OpenSpec workflow guidance

## Quick Start Guide

### Environment Setup
```bash
# Install dependencies (requires Python 3.14+)
uv install

# Install development dependencies
uv install --dev
```

### Development Commands
```bash
# Lint code
./start-lint.sh --check
./start-lint.sh --fix
./start-lint.sh --format

# Type checking
./start-type-check.sh --check
./start-type-check.sh --stats

# Unit testing
./start-unittest.sh --run
./start-unittest.sh --coverage
```

## Key Technologies

- **FastMCP**: MCP server framework
- **PyGithub**: GitHub API client
- **Pydantic v2**: Data validation
- **anyio**: Async compatibility layer
- **Dynaconf**: Configuration management
- **OpenSpec**: Spec-driven development workflow

## Documentation References

- **Full Roadmap:** `ROADMAP.md` - Detailed planning with version targets
- **Comprehensive Development Plan:** `COMPREHENSIVE-DEVELOPMENT-PLAN.md` - Implementation tasks and status
- **Architecture Guides:** Individual `AGENTS.md` files in each directory

## Code Quality Standards

- **Linting**: 0 errors with ruff
- **Type Checking**: 0 errors with ty
- **Testing**: 863+ tests passing, ~70% coverage
- **Architecture**: Clean Architecture with proper layer separation
- **Documentation**: Comprehensive AGENTS.md files across all layers

## Recent Refactoring (v0.4.9)

### Phase 0-4: Foundation Complete
- Dependency injection infrastructure (ServiceContainer, ServiceFactory)
- VCS provider abstraction (multi-provider system)
- Plugin system (modular tool architecture)
- Clean architecture compliance (no layer violations, no circular dependencies)

### Next Development Focus

- Continue refactoring smaller components per COMPREHENSIVE-DEVELOPMENT-PLAN.md
- Add more VCS providers (Bitbucket, Gitea)
- Implement additional MCP tools (describe PR, approve PR, review PR)
- Expand test coverage to >85%
