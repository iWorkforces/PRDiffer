# Security Infrastructure

This directory contains security components for input validation and sanitization to prevent common security vulnerabilities in the PRDiffer MCP server.

**Current Version:** 0.4.8

## Overview

The security layer provides comprehensive input validation and sanitization to protect against:
- SQL injection attacks
- Command injection attacks
- Path traversal attacks
- XSS (Cross-Site Scripting) attacks
- Malicious URLs
- Invalid data formats
- Log injection attacks

## Components

### InputValidator (`input_validator.py`)

Comprehensive input validation and sanitization class with both class methods and convenience functions.

#### Key Features

**1. GitHub URL Validation**
- Validates GitHub PR URLs against strict regex patterns
- Enforces HTTPS-only URLs
- Length limits (max 2000 characters)
- Detects suspicious patterns before parsing
- Returns validated tuple: `(owner, repo, pr_number)`

```python
from prdiffer.infrastructure.security.input_validator import validate_github_url

# Valid URL
owner, repo, pr_number = validate_github_url("https://github.com/owner/repo/pull/123")

# Invalid URL raises InvalidURLError
validate_github_url("http://github.com/owner/repo/pull/123")  # Not HTTPS
validate_github_url("https://github.com/owner/repo/pull/123; rm -rf /")  # Suspicious pattern
```

**2. Repository Identifier Validation**
- Validates "owner/repo" format
- Enforces GitHub naming conventions:
  - Owner: max 39 chars, alphanumeric + hyphens/underscores
  - Repo: max 100 chars, alphanumeric + hyphens/underscores/dots
- Returns validated tuple: `(owner, repo)`

```python
from prdiffer.infrastructure.security.input_validator import validate_repository_identifier

# Valid identifier
owner, repo = validate_repository_identifier("anthropics/claude-code")

# Invalid identifier raises InvalidRepositoryError
validate_repository_identifier("../etc/passwd")  # Path traversal attempt
```

**3. String Sanitization**
- Removes control characters (except common whitespace)
- Checks for null bytes
- Enforces length limits (default: 1000 chars)
- Detects suspicious patterns

```python
from prdiffer.infrastructure.security.input_validator import sanitize_string

# Sanitize user input
safe_string = sanitize_string(user_input, max_length=500)
```

**4. PR Number Validation**
- Ensures positive integers
- Reasonable upper limit (max 1,000,000)

```python
from prdiffer.infrastructure.security.input_validator import InputValidator

pr_number = InputValidator.validate_pr_number(123)  # Returns 123
InputValidator.validate_pr_number(-1)  # Raises InvalidPRNumberError
```

**5. Token Validation**
- Validates authentication token format
- Length constraints: 20-500 characters
- Alphanumeric with limited special chars (-, _, .)
- No leading/trailing whitespace

```python
from prdiffer.infrastructure.security.input_validator import validate_token

token = validate_token("ghp_1234567890abcdefghijklmnop")
```

**6. User ID Validation**
- Max 100 characters
- Alphanumeric with @, -, _, . allowed

```python
from prdiffer.infrastructure.security.input_validator import validate_user_id

user_id = validate_user_id("user@example.com")
```

**7. File Path Validation**
- Detects path traversal attempts
- Blocks absolute paths
- Max 500 characters

```python
from prdiffer.infrastructure.security.input_validator import InputValidator

path = InputValidator.validate_file_path("cache/pr_123.json")
```

**8. Safe Logging**
- Sanitizes values for secure logging
- Truncates long values (default: 200 chars)
- Removes control characters
- Prevents log injection

```python
from prdiffer.infrastructure.security.input_validator import InputValidator

safe_value = InputValidator.sanitize_for_logging(user_input, max_length=200)
logger.info(f"User input: {safe_value}")
```

**9. Branch/Ref Validation**

- Validates Git branch and reference names against Git naming rules
- Enforces Git ref naming conventions (git-check-ref-format rules)
- Prevents injection attacks through malicious branch names
- Max 255 characters, alphanumeric with safe separators

```python
from prdiffer.infrastructure.security.input_validator import validate_branch_name

# Valid branch names
branch = validate_branch_name("feature/new-functionality")  # Valid
branch = validate_branch_name("bugfix/issue-123")  # Valid
branch = validate_branch_name("release/v1.0.0")  # Valid

# Invalid branch names raise InputSanitizationError
validate_branch_name("../../etc/passwd")  # Path traversal - rejected
validate_branch_name("feature; rm -rf /")  # Command injection - rejected
validate_branch_name("-h")  # Looks like a flag - rejected
```

**Git Ref Naming Rules:**

- Cannot begin or end with slash (`/`)
- Cannot have consecutive slashes (`//`)
- Cannot contain `..`, `.`, `@`, `:`, `@{`, spaces, control chars
- Cannot start with a dash (`-`)
- Max length 255 characters
- Must be valid UTF-8

#### Validation Patterns

**Command Injection Detection**:
- Shell metacharacters: `; & | ` $ ( )`
- Command substitution: `$(`, backticks
- Pattern: `r'[;&|`$]'`, `r'\$\('`, `r'`'`

**Path Traversal Detection**:
- Parent directory: `..`
- Home directory: `~/`
- System directories: `/etc/`, `/var/`, `/usr/`

**SQL Injection Detection**:
- SQL comments: `--`, `#`, `/* */`
- SQL keywords: `union`, `select`, `insert`, `update`, `delete`, `drop`, `create`, `alter`
- Stored procedures: `exec`, `execute`, `xp_`

#### Security Exceptions

All validation errors raise specific exceptions from `prdiffer.domain.exceptions`:

- `InvalidURLError`: Malformed or suspicious URLs
- `InvalidRepositoryError`: Invalid repository identifiers
- `InvalidPRNumberError`: Invalid PR numbers
- `InputSanitizationError`: General input validation failures
- `SuspiciousOperationError`: Detected security threats

## Usage Guidelines

### 1. Always Validate User Input

**Before processing any user input**, validate it using appropriate `InputValidator` methods:

```python
from prdiffer.infrastructure.security.input_validator import InputValidator

class MyService:
    def __init__(self):
        self._validator = InputValidator()

    def process_pr_url(self, url: str):
        # Validate URL before processing
        owner, repo, pr_number = self._validator.validate_github_url(url)
        # Now safe to use owner, repo, pr_number
```

### 2. Use Convenience Functions

For quick validation, use module-level convenience functions:

```python
from prdiffer.infrastructure.security.input_validator import (
    validate_github_url,
    validate_repository_identifier,
    sanitize_string,
    validate_token,
    validate_user_id,
)

# Direct function calls without instantiating class
owner, repo, pr = validate_github_url(url)
safe_input = sanitize_string(user_input)
```

### 3. Handle Security Exceptions

Always catch and handle security exceptions appropriately:

```python
from prdiffer.domain.exceptions import (
    InvalidURLError,
    SuspiciousOperationError,
)
from prdiffer.infrastructure.security.input_validator import InputValidator

try:
    owner, repo, pr = InputValidator.validate_github_url(url)
except InvalidURLError as e:
    logger.warning(f"Invalid URL: {e}")
    return {"error": "Invalid GitHub PR URL"}
except SuspiciousOperationError as e:
    logger.error(f"Security threat detected: {e}")
    return {"error": "Suspicious URL pattern detected"}
```

### 4. Safe Logging Practices

Always sanitize values before logging:

```python
from prdiffer.infrastructure.security.input_validator import InputValidator

# Unsafe logging (vulnerable to log injection)
logger.info(f"Processing URL: {user_url}")  # DON'T DO THIS

# Safe logging
safe_url = InputValidator.sanitize_for_logging(user_url)
logger.info(f"Processing URL: {safe_url}")  # DO THIS
```

### 5. Integration Pattern

Example integration in application layer:

```python
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.domain.exceptions import (
    InvalidURLError,
    InputSanitizationError,
    SuspiciousOperationError,
)

class FastMCPServer:
    def __init__(self, ...):
        # Initialize security validator
        self._input_validator = InputValidator()

    async def handle_request(self, pr_url: str):
        try:
            # Sanitize and validate URL
            pr_url = self._input_validator.sanitize_string(pr_url, max_length=2000)
            owner, repo, pr_number = self._input_validator.validate_github_url(pr_url)

            # Process with validated inputs
            return await self._process_pr(owner, repo, pr_number)

        except (InvalidURLError, InputSanitizationError, SuspiciousOperationError) as e:
            # Log safely
            safe_url = self._input_validator.sanitize_for_logging(pr_url) if pr_url else None
            self._logger.warning(
                "Security validation failed",
                url=safe_url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ValueError(f"Invalid request: {e}")
```

## Extending Security Components

### Adding New Validation Methods

When adding new validation methods:

1. **Add validation patterns as class attributes**:
```python
class InputValidator:
    # Add new pattern
    NEW_PATTERN = re.compile(r'^[a-z0-9]+$')
```

2. **Implement validation method**:
```python
@classmethod
def validate_new_field(cls, value: str) -> str:
    """Validate new field.

    Args:
        value: Value to validate

    Returns:
        Validated value

    Raises:
        InputSanitizationError: If validation fails
    """
    if not cls.NEW_PATTERN.match(value):
        raise InputSanitizationError("Invalid format")
    return value
```

3. **Add convenience function**:
```python
def validate_new_field(value: str) -> str:
    """Convenience function for new field validation."""
    return _validator.validate_new_field(value)
```

4. **Add tests** (in appropriate test file):
```python
def test_validate_new_field_valid():
    result = InputValidator.validate_new_field("abc123")
    assert result == "abc123"

def test_validate_new_field_invalid():
    with pytest.raises(InputSanitizationError):
        InputValidator.validate_new_field("ABC-123")
```

### Adding New Suspicious Patterns

To detect new attack patterns:

```python
class InputValidator:
    # Add new pattern list
    NEW_ATTACK_PATTERNS = [
        r'pattern1',
        r'pattern2',
    ]

    @classmethod
    def _contains_suspicious_patterns(cls, value: str) -> bool:
        """Check if value contains suspicious patterns."""
        value_lower = value.lower()

        # Existing checks...

        # Add new check
        for pattern in cls.NEW_ATTACK_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True

        return False
```

## Testing Security Components

### Unit Tests

Write comprehensive unit tests for all validation methods:

```python
import pytest
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.domain.exceptions import InvalidURLError, SuspiciousOperationError

class TestInputValidator:
    def test_valid_github_url(self):
        owner, repo, pr = InputValidator.validate_github_url(
            "https://github.com/owner/repo/pull/123"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert pr == 123

    def test_command_injection_detected(self):
        with pytest.raises(SuspiciousOperationError):
            InputValidator.validate_github_url(
                "https://github.com/owner/repo/pull/123; rm -rf /"
            )

    def test_sql_injection_detected(self):
        with pytest.raises(SuspiciousOperationError):
            InputValidator.sanitize_string("'; DROP TABLE users; --")

    def test_path_traversal_detected(self):
        with pytest.raises(SuspiciousOperationError):
            InputValidator.validate_file_path("../../etc/passwd")
```

### Security Testing

Test for common attack vectors:

1. **Command Injection**: `; ls`, `$(whoami)`, backticks
2. **SQL Injection**: `' OR '1'='1`, `UNION SELECT`, `--`
3. **Path Traversal**: `../../../`, `~/.ssh/`, `/etc/passwd`
4. **XSS**: `<script>`, javascript:, `onerror=`
5. **Log Injection**: `\n\r`, control characters
6. **Length Attacks**: Very long strings (DoS)

## Best Practices

1. **Defense in Depth**: Use multiple validation layers
2. **Fail Securely**: Reject invalid input rather than trying to fix it
3. **Whitelist Over Blacklist**: Prefer allowing known-good patterns over blocking known-bad
4. **Length Limits**: Always enforce reasonable length limits
5. **Safe Logging**: Never log unsanitized user input
6. **Clear Errors**: Provide clear error messages without exposing system details
7. **Regular Updates**: Keep patterns updated as new attack vectors emerge
8. **Audit Trail**: Log all security validation failures for monitoring

## Integration with MCP Server

The `InputValidator` is integrated into `FastMCPServer` (prdiffer/application/mcp_server.py):

- **Initialization**: Line 84
- **URL Validation**: Line 153 (`_parse_pr_url` method)
- **Parameter Sanitization**: Lines 222-232 (`get_pr_diff` tool)
- **Exception Handling**: Lines 290-314
- **Safe Logging**: Lines 309, 329

All user-facing tools should follow this integration pattern.

## References

- OWASP Input Validation Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- OWASP Injection Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html
- GitHub API Documentation: https://docs.github.com/en/rest