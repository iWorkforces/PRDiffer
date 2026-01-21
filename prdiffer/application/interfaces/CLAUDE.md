# CLAUDE.md - Application Interfaces

This file provides guidance for working with the Interfaces layer of the PRDiffer Application.

**Current Version:** 0.4.8

## Interfaces Overview

The interfaces layer contains specialized interfaces that handle cross-cutting concerns and provide enhanced functionality for the MCP server. These interfaces implement domain service contracts and provide application-specific adaptations.

## Key Interface Components

### Health Monitor (`health_monitor.py`)

**Primary Responsibilities:**
- System health tracking and reporting
- Performance metrics collection
- Resource usage monitoring
- Health status aggregation from multiple sources

**Key Features:**
- **Health Checks**: Automated health checks for GitHub API, AI services, and internal components
- **Metrics Collection**: Real-time collection of performance and usage metrics
- **Health Alerts**: Proactive alerting for health degradation or failures
- **Status Aggregation**: Combines health status from all application components

### Metrics Tracker (`metrics_tracker.py`)

**Primary Responsibilities:**
- Application performance metrics tracking
- Request/response statistics collection
- GitHub API usage analytics
- AI service performance monitoring

**Key Features:**
- **Performance Metrics**: Track response times, throughput, and error rates
- **Resource Metrics**: Monitor memory usage, CPU utilization, and file processing
- **API Metrics**: Track rate limits, retry attempts, and API success rates
- **Custom Metrics**: Plugin-based system for domain-specific metrics

### PR Operation Handler (`pr_operation_handler.py`)

**Primary Responsibilities:**
- Pull request processing orchestration
- File processing workflow management
- Parallel processing coordination
- Error recovery and retry logic

**Key Features:**
- **Workflow Management**: Coordinates the complete PR processing pipeline
- **Parallel Processing**: Manages concurrent file processing and API calls
- **Error Recovery**: Implements retry and fallback strategies for failures
- **Progress Tracking**: Provides processing status and progress updates

### Rate Limiter (`rate_limiter.py`)

**Primary Responsibilities:**
- GitHub API rate limiting enforcement
- Per-repository and global rate tracking
- Dynamic rate adjustment based on usage patterns
- Queue management for rate-limited requests

**Key Features:**
- **Adaptive Limiting**: Adjusts rates based on API health and load
- **Token Bucket**: Implements token bucket algorithm for smooth rate limiting
- **Queue Management**: Handles request queuing during rate limit situations
- **Backpressure**: Provides backpressure signals to prevent overload

### Server Configuration (`server_configuration.py`)

**Primary Responsibilities:**
- FastMCP server configuration management
- Transport protocol setup and validation
- Environment-specific configuration handling
- Configuration validation and error reporting

**Key Features:**
- **Transport Config**: Configures stdio, HTTP, SSE, and streamable-http transports
- **Environment Handling**: Manages configuration for development, production, testing
- **Validation**: Validates configuration values and provides meaningful errors
- **Runtime Updates**: Supports dynamic configuration updates where possible

### URL Validator (`url_validator.py`)

**Primary Responsibilities:**
- GitHub URL parsing and validation
- Repository access verification
- URL format standardization
- Security validation for URLs

**Key Features:**
- **Format Validation**: Ensures URLs follow expected GitHub patterns
- **Repository Access**: Verifies accessibility and permissions for repositories
- **URL Normalization**: Standardizes different URL formats to canonical form
- **Security Checks**: Validates URLs for potential security risks

## Development Guidelines

### Interface Design Principles
- **Domain-Driven**: Interfaces implement contracts from the domain layer
- **Dependency Injection**: Accept dependencies through constructors
- **Configuration-Based**: Behavior controlled through settings service
- **Testability**: Designed for easy mocking and unit testing

### Adding New Interfaces
When creating new interfaces:
1. Define the interface contract in the domain layer first
2. Implement the interface with proper error handling and logging
3. Add comprehensive unit tests with mocked dependencies
4. Update this documentation with the new component details

### Testing Strategy
- **Unit Tests**: Test each interface implementation in isolation
- **Integration Tests**: Verify interfaces work with actual dependencies
- **Contract Tests**: Ensure implementations meet domain contract requirements
- **Performance Tests**: Validate performance characteristics under load

## Integration with Application Layer

Interfaces are integrated into the application through:
- **Dependency Injection**: Provided to services through constructor injection
- **Factory Patterns**: Created by factories with proper dependency resolution
- **Initialization Order**: Dependencies initialized in correct order during startup

## Configuration Integration

Interfaces utilize configuration from `settings.toml`:
```toml
[mcp.interfaces]
health_check_interval = 30
rate_limit_buffer = 100
url_validation_strict = true
metrics_retention_hours = 24
server_config_reload = false
```

## Error Handling and Monitoring

- **Structured Logging**: All interfaces use structured logging with context
- **Health Integration**: Interfaces report health status to health monitor
- **Metrics Integration**: Performance metrics automatically collected
- **Graceful Degradation**: Interfaces degrade gracefully on failures

## Performance Considerations

- **Efficient Processing**: Minimize processing overhead and optimize algorithms
- **Resource Management**: Proper resource cleanup and connection management
- **Caching**: Utilize caching where appropriate to reduce processing
- **Asynchronous Processing**: Support async operations for non-blocking behavior