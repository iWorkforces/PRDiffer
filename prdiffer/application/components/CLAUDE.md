# CLAUDE.md - Application Components

This file provides guidance for working with the Components layer of the PRDiffer Application.

**Current Version:** 0.4.8

## Components Overview

The components layer contains modular, reusable components that support the FastMCPServer implementation. These components provide specialized functionality for protocol handling, request processing, and MCP-specific operations.

## Key Components

### Authentication Middleware (`authentication.py`)

**Primary Responsibilities:**

- API key-based authentication and authorization
- SHA-256 hashed token storage for security
- Per-client rate limiting integration
- Client identifier extraction from headers

**Key Features:**

- **API Key Validation**: Validates keys against configured set with SHA-256 hashing
- **Admin Support**: Separate admin API key with elevated privileges
- **Runtime Management**: Add/remove API keys dynamically
- **Configuration**: Environment-based enable/disable

### Server Configuration (`server_configuration.py`)

**Primary Responsibilities:**

- Server configuration and setup management
- Logging configuration based on settings
- Configuration validation

**Key Features:**

- **Logging Setup**: Configures log level from settings
- **Server Info**: Provides metadata (version, transport, port)
- **Validation**: Validates transport, port, and GitHub settings
- **MCP Instructions**: Returns server capabilities description

### PR Operation Handler (`pr_operation_handler.py`)

**Primary Responsibilities:**

- Handles PR-related operations (get diff, describe, approve, review)
- Manages repository caching for efficiency
- Coordinates with domain use cases for business logic
- Validates PR URLs and parses components

**Key Features:**

- **Repository Caching**: Reuses GitHubPRDiffRepository instances when available
- **URL Parsing**: Extracts owner, repo name, and PR number from GitHub URLs
- **Error Handling**: Comprehensive error handling with sanitized logging
- **Lazy Initialization**: Repository objects initialized only when needed

**Usage Pattern:**

```python
handler = PROperationHandler(
    github_repository_class=GitHubPRDiffRepository,
    cache_service=cache_service,
    repository_cache_service=repo_cache_service
)
result = await handler.get_pr_diff("https://github.com/owner/repo/pull/123")
```

### Rate Limiter (`rate_limiter.py`)

**Primary Responsibilities:**

- Enforces rate limits on API requests
- Per-client rate limiting using authenticated client_id or IP address
- Token bucket algorithm for burst limit protection

**Key Features:**

- **Per-Client Limits**: Each authenticated client has independent rate limits
- **Configurable Limits**: Requests per minute and burst size from settings
- **Token Bucket**: Allows burst traffic while maintaining average rate
- **Rate Limit Headers**: Returns X-RateLimit-* headers for client visibility

### Protocol Handler (`protocols.py`)

**Primary Responsibilities:**

- MCP protocol message processing and validation
- Request/response serialization and deserialization
- Protocol-specific error handling and formatting
- Transport layer abstraction for different MCP protocols

**Key Features:**

- **Message Validation**: Validates incoming MCP messages against protocol specifications
- **Serialization**: Converts between internal data structures and MCP protocol formats
- **Error Handling**: Formats errors according to MCP standards
- **Transport Compatibility**: Abstracts differences between stdio, HTTP, and SSE transports

### Metrics Tracker (`metrics_tracker.py`)

**Primary Responsibilities:**

- Tracks performance metrics for monitoring
- Records request counts, success/failure rates
- Provides observability for server health

### Authentication Middleware (`authentication.py`)

**Primary Responsibilities:**

- API key-based authentication and authorization
- Per-client rate limiting integration
- SHA-256 hashed token storage for security
- Client identifier extraction for rate limiting

**Key Features:**

- **API Key Authentication**: Validates API keys against configured set
- **SHA-256 Hashing**: Securely stores API key hashes instead of plain text
- **Admin API Key**: Separate admin key with elevated privileges
- **Per-Client Rate Limiting**: Integration with rate limiter using authenticated client_id
- **Configuration-Based**: Enable/disable via environment variables
- **Multiple API Keys**: Support for multiple valid API keys

**Key Methods:**
- `authenticate(api_key)` - Authenticates request using API key
- `extract_client_identifier(headers)` - Extracts API key from headers (X-API-Key, Authorization Bearer)
- `validate_api_key_format(api_key)` - Validates API key format
- `add_api_key(api_key)` - Runtime API key addition
- `remove_api_key(api_key)` - Runtime API key removal
- `get_status()` - Returns authentication configuration status

**Usage Pattern:**
```python
auth = AuthenticationMiddleware(logger)
is_authenticated, client_id = auth.authenticate(api_key)

# Extract from headers
api_key, client_id = auth.extract_client_identifier(request_headers)

# Check if authentication is enabled
if auth.is_authentication_enabled():
    # Require authentication
    pass
```

**Environment Configuration:**
- `MCP_AUTH_ENABLED` - Enable/disable authentication (default: false)
- `MCP_API_KEYS` - Comma-separated list of API keys
- `MCP_ADMIN_API_KEY` - Admin API key with elevated privileges

### Server Configuration (`server_configuration.py`)

**Primary Responsibilities:**

- Server configuration and setup management
- Logging configuration based on settings
- Server information and metadata
- Configuration validation

**Key Features:**

- **Logging Setup**: Configures log level and handlers based on settings
- **Server Info**: Provides server metadata (name, version, transport, port)
- **MCP Instructions**: Returns server capabilities and tool descriptions
- **Configuration Validation**: Validates transport, port, and GitHub settings
- **Feature Detection**: Reports enabled features (caching, rate limiting, metrics)

**Key Methods:**
- `setup_logging()` - Configures logging based on settings
- `get_server_info()` - Returns server information dictionary
- `get_mcp_instructions()` - Returns MCP server instructions for clients
- `validate_configuration()` - Validates server configuration and returns ValidationResult

**Usage Pattern:**
```python
config = ServerConfiguration(settings_service, logger)

# Setup logging
config.setup_logging()

# Get server information
info = config.get_server_info()
# Returns: {"name": "prdiffer", "version": "0.3.3", ...}

# Validate configuration
validation = config.validate_configuration()
if validation["valid"]:
    # Configuration is valid
    pass
```

**ValidationResult Type:**
```python
{
    "valid": bool,        # Overall validation status
    "warnings": List[str],  # Configuration warnings
    "errors": List[str]     # Configuration errors
}
```

### Health Monitor (`health_monitor.py`)

**Primary Responsibilities:**

- Performs health checks on server components
- Monitors GitHub API connectivity
- Provides health status endpoints

## Development Guidelines

### Component Design Principles
- **Single Responsibility**: Each component focuses on a specific aspect of application functionality
- **Dependency Injection**: Components receive dependencies rather than creating them
- **Testability**: Components designed for easy unit testing with mocked dependencies
- **Configuration**: Component behavior can be configured via settings service

### Adding New Components
When creating new components:
1. Define clear interfaces in the domain layer if extending core functionality
2. Implement as pure functions or classes with minimal side effects
3. Add comprehensive unit tests
4. Update this documentation with component details

### Testing Strategy
- **Unit Tests**: Test each component in isolation with mocked dependencies
- **Integration Tests**: Verify component interactions within the application layer
- **Performance Tests**: Ensure components meet performance requirements
- **Protocol Compliance**: Validate protocol handling against MCP specifications

## Integration with Application Layer

Components are integrated into the FastMCPServer through dependency injection:
- Components are instantiated by the factory or server initialization
- Dependencies are passed through constructor injection
- Configuration is provided via the settings service

## Configuration

Components may require configuration through `settings.toml`:
```toml
[mcp.protocols]
validation_enabled = true
serialization_format = "json"
max_message_size = 1048576  # 1MB
```

## Protocol Compliance

All components in this layer should maintain:
- **MCP Spec Compliance**: Follow current MCP protocol specifications
- **Backward Compatibility**: Support older protocol versions when possible
- **Error Handling**: Provide clear, actionable error messages
- **Performance**: Efficient processing without blocking or resource exhaustion