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
│   └── usecases/               # Business use cases
│       └── prompt/            # AI prompt generation use cases
├── application/                # Application layer - orchestration
│   └── mcp_server.py          # FastMCP server implementation
└── infrastructure/            # Infrastructure layer - external integrations
    ├── github_repository.py   # GitHub API repository implementation
    ├── prompt_repository.py   # AI prompt repository implementation
    ├── settings.py            # Configuration management
    ├── cache_service.py       # Caching infrastructure
    ├── github/               # GitHub-specific components
    ├── utils/                # Utility components
    └── logging/              # Logging infrastructure
```

## Architecture Layers

### Domain Layer (`domain/`)
The innermost layer containing:
- **Entities**: `FilePatchInfo`, `PRDiff`, `ExtraPRDiff`, `PromptRequest`, `PRDetails` - core business objects
- **Repository Interfaces**: `PRDiffRepositoryInterface`, `PromptRepositoryInterface` - data access contracts
- **Service Interfaces**: Abstract contracts for external services
- **Use Cases**: `GetPRDiffUseCase` and prompt use cases - business logic orchestration
- **No External Dependencies**: Pure business logic with no framework coupling

### Application Layer (`application/`)
The orchestration layer containing:
- **MCP Server**: FastMCP server implementation exposing tools
- **Use Case Coordination**: Wires together domain use cases with infrastructure
- **Dependency Injection**: Acts as composition root for the application
- **Protocol Handling**: MCP protocol implementation and tool exposure

### Infrastructure Layer (`infrastructure/`)
The outermost layer containing:
- **External Integrations**: GitHub API, AI services, file system, network
- **Framework Dependencies**: FastMCP, PyGithub, Dynaconf
- **Configuration**: Settings management and environment handling
- **Cross-Cutting Concerns**: Logging, caching, retry logic, prompt engineering

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
Configuration is managed through `settings.toml` with environment overrides:
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

[development]
  [development.app]
  debug = true
  log_level = "DEBUG"
```

### Environment Variables
- `ENV_FOR_DYNACONF`: Environment selection (development, production, testing)
- `GITHUB_TOKEN`: GitHub personal access token
- `AI_SERVICE_TOKEN`: AI service API token (if required)
- `AI_SERVICE_URL`: AI service endpoint URL (if custom)
- `TRANSPORT`: MCP transport mode (stdio, http, sse)
- `PORT`: Server port for HTTP/SSE transports

## Key Features

### GitHub Integration
- **PR Analysis**: Complete pull request diff analysis with full file context
- **Rate Limiting**: Intelligent handling of GitHub API rate limits
- **Caching**: Commit-based caching with automatic invalidation
- **File Filtering**: Configurable ignore patterns and valid extensions

### AI-Powered Prompt Generation
- **PR Description**: AI-generated pull request descriptions
- **Code Review**: AI-powered code review and suggestions
- **Changelog Updates**: Automated changelog entry generation
- **System Prompts**: Context-aware system prompt engineering

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
from ccpragents import GitHubPRDiffRepository, PromptRepository, get_settings_service
from ccpragents.domain.usecases.prompt import DescribePRUserPromptUseCase
from ccpragents.server import main

# Use repository directly
repo = GitHubPRDiffRepository("owner", "repo", 123)
diff = await repo.get_pr_diff()

# Use prompt use cases
prompt_repo = PromptRepository()
describer = DescribePRUserPromptUseCase(prompt_repo)
prompt = await describer.execute(pr_details, commit_messages, diff_content)

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
- **AI Service**: Configure AI service credentials if using prompt features

### Production Configuration
- **Logging**: Set appropriate log levels for production
- **Rate Limits**: Configure GitHub API rate limits based on token type
- **AI Rate Limits**: Configure AI service rate limits and quotas
- **Caching**: Tune cache settings for optimal performance
- **Resource Limits**: Set file processing limits based on available resources

### Monitoring and Maintenance
- **Log Analysis**: Monitor logs for errors and performance issues
- **API Usage**: Track GitHub API usage to avoid rate limits
- **AI Service Usage**: Monitor AI API usage and costs
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