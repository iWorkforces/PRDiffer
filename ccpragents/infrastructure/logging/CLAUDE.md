# CLAUDE.md - Logging Infrastructure

This file provides guidance for working with the logging infrastructure of CCPRAgents.

## Overview

This directory contains logging infrastructure components that provide structured, colored console logging for the application. The logging system follows Clean Architecture principles with a domain interface and infrastructure implementation.

## Components

### Exception Sanitizer (`exception_utils.py`)

**ExceptionSanitizer**

- Redacts sensitive data from exception messages before logging
- Prevents token exposure through error logs
- Handles GitHub tokens, passwords, emails, IP addresses
- Used throughout codebase (15+ locations) for secure logging

**Key Features:**

- **Token Redaction**: GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_ prefixes)
- **Password Redaction**: Generic password/passwd/pwd keywords
- **PII Protection**: Email and IP address partial redaction
- **Comprehensive Patterns**: Covers common sensitive data formats

**Redaction Examples:**

```python
from ccpragents.infrastructure.logging.exception_utils import sanitize_exception_for_logging

# GitHub token redaction
exception = Exception("Failed with token: ghp_1234567890abcdef")
sanitized = sanitize_exception_for_logging(exception)
# Result: "Failed with token: ghp_*****"

# Password redaction
exception = Exception("Authentication failed: password=secret123")
sanitized = sanitize_exception_for_logging(exception)
# Result: "Authentication failed: password=*****"

# Email redaction
exception = Exception("User user@example.com not found")
sanitized = sanitize_exception_for_logging(exception)
# Result: "User u***@e***.com not found"

# IP redaction
exception = Exception("Connection from 192.168.1.100")
sanitized = sanitize_exception_for_logging(exception)
# Result: "Connection from 192.168.*.*"
```

**Usage Pattern:**

```python
try:
    result = risky_github_api_call()
except Exception as e:
    sanitized = sanitize_exception_for_logging(e)
    logger.error("GitHub API failed", extra=sanitized)
```

**Redaction Patterns:**

- **GitHub Tokens**: `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_` followed by redaction
- **Generic Tokens**: `token`, `apikey`, `api_key`, `access_token` followed by `=` or `:`
- **Passwords**: `password`, `passwd`, `pwd` keywords
- **Emails**: Partially masked (u***@d***.com format)
- **IPs**: Last octet masked (192.168.*.*)

### Console Logger (`console_logger.py`)

**ConsoleLogger**
- Implements `LoggerServiceInterface` from domain layer
- Provides ANSI color-coded console output for different log levels
- Supports structured logging with context data via `**kwargs`
- Routes errors and critical messages to stderr, info/debug to stdout

**Log Levels and Colors:**
- **DEBUG**: Cyan - Detailed diagnostic information
- **INFO**: Green - General information about application flow
- **WARNING**: Yellow - Warning messages for potential issues
- **ERROR**: Red - Error conditions that don't stop execution
- **CRITICAL**: Magenta - Critical errors that may cause application failure

**Key Features:**
- **ANSI Color Codes**: Visual distinction between log levels in terminal output
- **Structured Logging**: Support for additional context via keyword arguments
- **Stream Routing**: Errors/critical to stderr, info/debug/warning to stdout
- **Timestamp Formatting**: ISO format timestamps for log entries
- **Context Preservation**: Maintains additional data passed with log messages

### Global Access Pattern

The logging system uses a singleton pattern for easy access throughout the application:

```python
from ccpragents.infrastructure.logging.console_logger import get_logger

logger = get_logger()
logger.info("Application started")
logger.error("Failed to process file", filename="test.py", error_code=404)
```

## Architecture Integration

### Domain Interface Compliance
The console logger implements the domain service interface:
```python
# Domain interface (abstract)
class LoggerServiceInterface(ABC):
    def debug(self, message: str, **kwargs) -> None: ...
    def info(self, message: str, **kwargs) -> None: ...
    def warning(self, message: str, **kwargs) -> None: ...
    def error(self, message: str, **kwargs) -> None: ...
    def critical(self, message: str, **kwargs) -> None: ...

# Infrastructure implementation
class ConsoleLogger(LoggerServiceInterface):
    # Concrete implementation with ANSI colors
```

### Configuration Integration
The logger integrates with the settings service:
- **Log Level Filtering**: Based on `app.log_level` setting
- **Debug Mode**: Enhanced debug output when `app.debug` is True
- **Format Configuration**: Customizable timestamp and message formats

### Dependency Injection
Components receive logger instances through dependency injection:
```python
class GitHubRepository:
    def __init__(self, logger=None):
        self.logger = logger or get_logger()
```

## Usage Patterns

### Basic Logging
```python
logger = get_logger()

# Simple messages
logger.info("Processing started")
logger.warning("Rate limit approaching")
logger.error("API call failed")

# Messages with context
logger.info("File processed", 
           filename="script.py", 
           lines_processed=150, 
           processing_time=0.5)
```

### Structured Logging
Take advantage of keyword arguments for additional context:
```python
logger.info("PR analysis complete",
           pr_number=123,
           files_changed=5,
           additions=50,
           deletions=25,
           processing_time_ms=1500)
```

### Error Logging with Context
```python
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed", 
                operation="risky_operation",
                error_type=type(e).__name__,
                error_message=str(e))
```

### Performance Logging
For performance-critical paths, check log level before expensive operations:
```python
if logger.level <= logging.DEBUG:
    logger.debug("Detailed performance data", 
                 execution_time=timer.elapsed(),
                 memory_usage=get_memory_usage(),
                 api_calls_made=api_counter.value)
```

## Development Guidelines

### Log Level Usage
- **DEBUG**: Detailed diagnostic information, typically only of interest when diagnosing problems
- **INFO**: General information about what the application is doing
- **WARNING**: An indication that something unexpected happened, but the application is still working
- **ERROR**: Due to a more serious problem, the software has not been able to perform some function
- **CRITICAL**: A serious error, indicating that the program itself may be unable to continue running

### Message Formatting
- **Concise**: Keep messages short and to the point
- **Descriptive**: Include enough context to understand what happened
- **Consistent**: Use consistent terminology and format across the application
- **Actionable**: When possible, indicate what action should be taken

### Context Data Guidelines
- **Relevant**: Only include data that helps understand the situation
- **Structured**: Use consistent key names across the application
- **Safe**: Never log sensitive information (tokens, passwords, personal data)
- **Typed**: Use appropriate data types (numbers as numbers, not strings)

### Performance Considerations
- **Level Checking**: Check log level before expensive context gathering
- **String Formatting**: Use lazy formatting with f-strings or % formatting
- **Memory Usage**: Don't keep large objects in log context
- **I/O Impact**: Consider the performance impact of frequent logging

## Testing Strategies

### Unit Testing Logging
```python
import io
import sys
from unittest.mock import patch

def test_error_logging():
    with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
        logger = get_logger()
        logger.error("Test error message")
        assert "Test error message" in mock_stderr.getvalue()
        assert "ERROR" in mock_stderr.getvalue()
```

### Integration Testing
Test that components use logging appropriately:
```python
def test_component_logging():
    with patch('ccpragents.infrastructure.logging.console_logger.get_logger') as mock_logger:
        component = SomeComponent()
        component.do_something_that_should_log()
        mock_logger.return_value.info.assert_called_with("Expected message")
```

### Log Output Validation
For critical logging scenarios, validate log output format and content:
```python
def test_structured_logging():
    logger = get_logger()
    with capture_logs() as captured:
        logger.info("Test message", key1="value1", key2=42)
        assert "Test message" in captured.output
        assert "key1" in captured.context
        assert captured.context["key2"] == 42
```

## Configuration

### Log Level Configuration
Set in `settings.toml`:
```toml
[default.app]
log_level = "INFO"
debug = false

[development.app]
log_level = "DEBUG"
debug = true
```

### Custom Logger Configuration
For advanced use cases, create custom logger instances:
```python
from ccpragents.infrastructure.logging.console_logger import ConsoleLogger

# Custom logger with specific configuration
custom_logger = ConsoleLogger()
custom_logger.set_level("WARNING")  # Only warnings and above
```

## Migration and Compatibility

### Legacy Logging Migration
When migrating from standard Python logging:
1. **Replace Imports**: Change from `import logging` to logger service
2. **Update Calls**: Replace `logging.info()` with `logger.info()`
3. **Add Context**: Take advantage of structured logging with `**kwargs`
4. **Stream Awareness**: Verify error/critical messages go to stderr

### Standard Library Integration
The console logger can coexist with standard Python logging:
```python
import logging
from ccpragents.infrastructure.logging.console_logger import get_logger

# Standard logging for third-party libraries
logging.getLogger('requests').setLevel(logging.WARNING)

# Application logging through our service
logger = get_logger()
logger.info("Application message")
```

## File Organization

```
ccpragents/infrastructure/logging/
├── __init__.py              # Public API exports
└── console_logger.py        # Console logger implementation with ANSI colors
```

## Future Enhancements

The logging infrastructure is designed to be extensible:
- **File Logging**: Add file-based logging implementations
- **Remote Logging**: Integrate with log aggregation services
- **Metrics Integration**: Add metrics collection alongside logging
- **Log Rotation**: Implement log rotation for file-based logging
- **Filtering**: Add advanced filtering capabilities