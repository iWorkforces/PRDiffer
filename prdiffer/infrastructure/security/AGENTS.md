# AGENTS.md - Infrastructure/Security

Security utilities: input validation, sanitization, injection detection.

## Guidelines

- Validate all inputs from external sources
- Sanitize user-provided data
- **Pattern-based injection detection** (command, path traversal, SQL)
- Hash sensitive data appropriately (SHA-256 for API keys)
- Reject suspicious patterns before processing

## Common Patterns

### InputValidator (Orchestrator)
```python
from prdiffer.domain.exceptions import ValidationError

class InputValidator:
    '''765-line orchestrator for injection detection + sanitization'''
    
    @staticmethod
    def validate_pr_url(url: str) -> None:
        if not url.startswith('https://github.com/'):
            raise ValidationError('Invalid GitHub PR URL format')
        
        # Check for injection patterns
        InjectionDetector.detect_all(url)
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        '''Remove dangerous patterns'''
        return Sanitizer.sanitize(text)
```

### InjectionDetector (Pattern-Based)
```python
import re

class InjectionDetector:
    '''267-line pattern-based threat detection'''
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r'\$\([^)]+\)',      # Command substitution
        r'`[^`]+`',          # Backticks
        r';\s*\w+',          # Command chaining
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\.',             # Parent directory
        r'~/',               # Home directory
        r'/etc/',            # System paths
        r'/var/',
        r'/usr/',
        r'[A-Za-z]:\\',      # Windows paths
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'--',               # SQL comments
        r'/\*.*\*/',         # SQL block comments
        r'\bUNION\b',        # UNION queries
        r'\bSELECT\b',
        r'\bINSERT\b',
        r'\bDELETE\b',
    ]
    
    @staticmethod
    def detect_all(text: str) -> None:
        '''Detect all injection patterns'''
        if InjectionDetector.has_command_injection(text):
            raise ValidationError('Command injection detected')
        if InjectionDetector.has_path_traversal(text):
            raise ValidationError('Path traversal detected')
        if InjectionDetector.has_sql_injection(text):
            raise ValidationError('SQL injection detected')
```

### Sanitizer (156-line)
```python
class Sanitizer:
    '''156-line input sanitization'''
    
    @staticmethod
    def sanitize(text: str) -> str:
        # Remove shell metacharacters
        text = re.sub(r'[;&|`$()<>]', '', text)
        # Remove script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE)
        return text.strip()
```

### API Key Hashing (SHA-256)
```python
import hashlib

def hash_api_key(api_key: str) -> str:
    '''SHA-256 hashing for API keys'''
    return hashlib.sha256(api_key.encode()).hexdigest()
```

## Anti-Patterns

- ❌ Logging sensitive data (tokens, API keys, passwords)
- ❌ Missing injection detection before processing
- ❌ Raw SQL queries (use parameterized)
- ❌ Weak hashing (MD5, SHA1) for secrets
- ❌ Bypassing input validation

## Security Patterns (Configurable via settings.toml)

```toml
[security]
# Pattern-based injection detection
command_injection_patterns = ['$(...)', '`...`', '; cmd']
path_traversal_patterns = ['..', '~/', '/etc/', '/var/']
sql_injection_patterns = ['--', '/*', 'UNION', 'SELECT']
```

## Files

- `input_validator.py`: Input validation orchestrator (765 lines)
- `injection_detector.py`: Pattern-based threat detection (267 lines)
- `sanitizer.py`: Input sanitization (156 lines)
