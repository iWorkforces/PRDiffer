# CLAUDE.md - CCPRAgents Main Package

This file provides guidance for working with the main CCPRAgents package structure.

## Package Overview

CCPRAgents is an MCP (Model Context Protocol) server that provides GitHub PR diff analysis capabilities. The package follows Clean Architecture principles with clear separation between domain, application, and infrastructure layers.

## Package Structure

```
ccpragents/
├── CLAUDE.md                    # This file - main package guidance
├── __init__.py                  # Package initialization
├── server.py                    # Main server entry point
├── domain/                      # Domain layer - business logic
│   ├── entities/               # Core business objects
│   ├── repositories/           # Repository interfaces
│   ├── services/               # Domain service interfaces
│   ├── usecases/               # Business use cases
│   └── factories/              # Factory interfaces for dependency inversion
├── application/                # Application layer - orchestration
│   ├── mcp_server.py          # FastMCP server implementation
│   ├── components/            # Application components
│   └── interfaces/            # Protocol definitions
└── infrastructure/            # Infrastructure layer - external integrations
    ├── github_repository.py   # GitHub API repository implementation
    ├── settings.py            # Configuration management
    ├── cache_service.py       # Caching infrastructure
    ├── repository_cache_service.py  # Repository instance caching
    ├── github/               # GitHub-specific components
    ├── utils/                # Utility components
    ├── logging/              # Logging infrastructure
    ├── security/             # Security and input validation
    ├── factories/            # Factory implementations
    └── services/             # Service implementations (PRDiffService)
```

## Architecture Layers

### Domain Layer (`domain/`)
The innermost layer containing:
- **Entities**: `FilePatchInfo`, `PRDiff` - core business objects
- **Repository Interfaces**: `PRDiffRepositoryInterface` - data access contracts
- **Service Interfaces**: Abstract contracts for external services
  - `CacheServiceInterface` - Caching abstraction
  - `SettingsServiceInterface` - Configuration abstraction
  - `LoggerServiceInterface` - Logging abstraction
  - `RepositoryCacheServiceInterface` - Repository instance caching
  - `DiffServiceInterface` - Diff operations abstraction
  - `GitHubAPIServiceInterface` - GitHub API abstraction
  - `PatternMatchingServiceInterface` - Pattern matching abstraction
  - `RetryServiceInterface` - Retry logic abstraction
  - `PRDiffServiceInterface` - PR diff operations abstraction
- **Use Cases**: `GetPRDiffUseCase` - business logic orchestration
- **Factory Interfaces**: `InfrastructureFactoryInterface` - dependency injection
- **No External Dependencies**: Pure business logic with no framework coupling

### Application Layer (`application/`)
The orchestration layer containing:
- **MCP Server**: FastMCP server implementation exposing tools
- **Use Case Coordination**: Wires together domain use cases with infrastructure
- **Dependency Injection**: Acts as composition root for the application
- **Protocol Handling**: MCP protocol implementation and tool exposure

### Infrastructure Layer (`infrastructure/`)
The outermost layer containing:
- **External Integrations**: GitHub API, file system, network
- **Framework Dependencies**: FastMCP, PyGithub, Dynaconf
- **Configuration**: Settings management and environment handling
- **Cross-Cutting Concerns**: Logging, caching, retry logic
- **Factory Implementation**: `InfrastructureFactory` - creates service instances
- **Service Implementations**: `GitHubPRDiffService` - PR diff operations
- **Security Components**: `InputValidator` - input validation and sanitization

## Dependency Flow

```
Application Layer
    ↓ (depends on)
Domain Layer
    ↑ (implemented by)
Infrastructure Layer
```

**Key Principle**: Dependencies point inward. Infrastructure implements domain interfaces.

## Main Entry Points

### Server Entry Point (`server.py`)
The main server launcher that:
- Initializes all services and dependencies
- Creates the FastMCP server with proper configuration
- Handles different transport modes (stdio, HTTP, SSE)
- Manages server lifecycle and error handling

### Application Server (`application/mcp_server.py`)
The FastMCP server implementation that:
- Exposes the `get_pr_diff` MCP tool
- Handles URL parsing and validation
- Manages caching and rate limiting
- Provides health checks and metrics

## Configuration Management

### Settings Structure
Configuration is managed through `settings.toml` with support for environment-specific overrides:
```toml
[default]
  [default.app]
  debug = false
  log_level = "INFO"
  max_files_allowed = 50

  [default.github]
  rate_limit = 5000
  timeout = 30
  ignore_patterns = ["*.lock", "node_modules/"]
  valid_extensions = [".py", ".js", ".ts", ".md"]
```

### Environment Variables
- `ENV_FOR_DYNACONF`: Environment selection (development, production, testing)
- `GITHUB_TOKEN`: GitHub personal access token
- `TRANSPORT`: MCP transport mode (stdio, http, sse)
- `PORT`: Server port for HTTP/SSE transports

## Key Features

### GitHub Integration
- **PR Analysis**: Complete pull request diff analysis with full file context
- **Rate Limiting**: Intelligent handling of GitHub API rate limits
- **Caching**: Commit-based caching with automatic invalidation
- **File Filtering**: Configurable ignore patterns and valid extensions


### MCP Protocol Support
- **Tool Exposure**: `get_pr_diff` tool for PR analysis
- **Multiple Transports**: stdio, HTTP, Server-Sent Events
- **Parameter Validation**: Robust URL parsing and validation
- **Error Handling**: Graceful error handling with meaningful messages

### Performance Optimization
- **Parallel Processing**: Concurrent file processing for large PRs
- **Batch Operations**: Efficient bulk file content retrieval
- **Intelligent Caching**: Multi-level caching strategy
- **Resource Limits**: Configurable limits to prevent resource exhaustion

### Security Architecture
- **API Key Authentication**: SHA-256 hashed token storage for secure access control
- **Per-Client Rate Limiting**: Rate limiting based on authenticated client identity
- **Input Validation**: Comprehensive validation for URLs, repository identifiers, and branch names
- **Exception Sanitization**: Automatic redaction of sensitive data (tokens, passwords, emails) from logs
- **Safe Logging**: All user inputs sanitized before logging to prevent log injection attacks
- **Branch/Ref Validation**: Git ref naming rules enforcement to prevent injection attacks

**Security Documentation**: See `SecurityUsageGuide.md` for comprehensive authentication setup, client connection examples, and troubleshooting.

### Thread Safety Guarantees
- **CacheService**: Fully thread-safe with `threading.RLock()` protection on all operations
- **RequestCoalescingService**: Memory-safe with maximum waiter limits (default: 100) and proper cleanup
- **FileProcessor**: Thread-safe cache with double-check locking pattern for race condition prevention
- **CacheDecorator**: Thread-safe caching mixin with reentrant lock protection
- **Anyio Async Primitives**: Uses `anyio` (Lock, Semaphore, Event) for portable async concurrency
- **Proper Exception Handling**: Assertions replaced with RuntimeError exceptions for production safety

**Thread Safety Patterns**:
- Reentrant locks (`RLock`) for recursive access patterns
- Double-check locking for performance with safety
- Atomic state management with proper cleanup on all exit paths
- Timeout protection with `anyio.fail_after()` to prevent indefinite waits

## Development Workflows

### Adding New Features
1. **Domain First**: Define entities and interfaces in domain layer
2. **Use Case Implementation**: Create or extend use cases
3. **Infrastructure Implementation**: Implement domain interfaces
4. **Application Integration**: Wire components in application layer
5. **Configuration**: Add necessary settings and environment variables

### Testing Strategy
- **Unit Tests**: Test each layer in isolation with mocked dependencies
- **Integration Tests**: Test layer interactions with real dependencies
- **End-to-End Tests**: Test complete workflows through MCP protocol
- **Performance Tests**: Validate performance with large PRs

### Debugging and Monitoring
- **Structured Logging**: Comprehensive logging with context
- **Health Checks**: Built-in health monitoring and metrics
- **Debug Mode**: Enhanced debug output in development
- **Error Tracking**: Detailed error reporting and stack traces

## Package Initialization

The `__init__.py` file provides:
- **Version Information**: Package version for reference
- **Public API**: Key classes and functions for external use
- **Import Convenience**: Easy access to main components

Example usage:
```python
from ccpragents.infrastructure import (
    GitHubPRDiffRepository,
    get_settings_service,
    get_cache_service
)
from ccpragents.server import main

# Use repository directly
repo = GitHubPRDiffRepository("owner", "repo", 123)
diff = await repo.get_pr_diff()

# Or run the MCP server
if __name__ == "__main__":
    main()
```

## Deployment Considerations

### Environment Setup
- **Python 3.13+**: Required Python version
- **Dependencies**: Install via `uv install` or `pip install -r requirements.txt`
- **Configuration**: Set up `settings.toml` and environment variables
- **GitHub Token**: Configure authentication for private repositories

### Production Configuration
- **Logging**: Set appropriate log levels for production
- **Rate Limits**: Configure GitHub API rate limits based on token type
- **Caching**: Tune cache settings for optimal performance
- **Resource Limits**: Set file processing limits based on available resources

### Monitoring and Maintenance
- **Log Analysis**: Monitor logs for errors and performance issues
- **API Usage**: Track GitHub API usage to avoid rate limits
- **Performance Metrics**: Monitor response times and resource usage
- **Updates**: Keep dependencies updated for security and performance

## Migration and Compatibility

### Version Compatibility
The package maintains backward compatibility for:
- **MCP Protocol**: Compatible with MCP client implementations
- **Configuration**: Settings file format and structure
- **API**: Public interfaces and method signatures

### Upgrade Considerations
When upgrading:
- **Review Settings**: Check for new configuration options
- **Update Dependencies**: Ensure compatible dependency versions
- **Test Functionality**: Validate critical workflows after upgrade
- **Monitor Performance**: Watch for performance regressions

This package structure provides a robust, maintainable foundation for GitHub PR diff analysis while maintaining clean separation of concerns and enabling easy testing and extension.