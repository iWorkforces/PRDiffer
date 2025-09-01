# CLAUDE.md - Application Components

This file provides guidance for working with the Components layer of the CCPRAgents Application.

## Components Overview

The components layer contains modular, reusable components that support the FastMCPServer implementation. These components provide specialized functionality for protocol handling, request processing, and MCP-specific operations.

## Key Components

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