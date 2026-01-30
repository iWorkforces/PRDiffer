"""Input validation and sanitization for security.

This module provides comprehensive input validation to prevent:
- SQL injection
- Command injection
- Path traversal
- XSS attacks
- Malicious URLs
- Invalid data formats
"""

import logging
import re
from dataclasses import dataclass
from typing import Pattern, TYPE_CHECKING

from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    InputSanitizationError,
    SuspiciousOperationError,
)

if TYPE_CHECKING:
    from prdiffer.infrastructure.settings import SettingsService

logger = logging.getLogger(__name__)


@dataclass
class SecurityPatterns:
    """Configurable security patterns loaded from settings.

    This dataclass provides configurable security patterns for detecting
    malicious input patterns. Patterns can be loaded from settings or
    use default values.

    Attributes:
        command_injection: List of regex patterns for command injection detection
        path_traversal: List of regex patterns for path traversal detection
        sql_injection: List of regex patterns for SQL injection detection
    """

    command_injection: list[str]
    path_traversal: list[str]
    sql_injection: list[str]

    @classmethod
    def from_settings(
        cls, settings_service: "SettingsService | None"
    ) -> "SecurityPatterns":
        """Load patterns from settings service.

        Args:
            settings_service: Settings service instance (optional)

        Returns:
            SecurityPatterns instance with configured patterns
        """
        # Default patterns
        defaults = cls(
            command_injection=[
                r"[;&|`$]",  # Shell metacharacters
                r"\$\(",  # Command substitution
                r"`",  # Backticks
            ],
            path_traversal=[
                r"\.\.",  # Parent directory (Unix)
                r"~/",  # Home directory (Unix)
                r"/etc/",  # System directories (Unix)
                r"/var/",
                r"/usr/",
                r"[a-zA-Z]:\\",  # Windows absolute paths
                r"\.\.\\",  # Windows parent directory
                r"\\\\",  # UNC paths
            ],
            sql_injection=[
                r"(?:--|#|/\*|\*/)",  # SQL comments
                r"\b(?:union|select|insert|update|delete|drop|create|alter)\b",
                r"(?:exec|execute|xp_)",
            ],
        )

        if settings_service is None:
            return defaults

        try:
            command = settings_service.get("security.command_injection_patterns", [])
            path = settings_service.get("security.path_traversal_patterns", [])
            sql = settings_service.get("security.sql_injection_patterns", [])

            if command or path or sql:
                return cls(
                    command_injection=command
                    if command
                    else defaults.command_injection,
                    path_traversal=path if path else defaults.path_traversal,
                    sql_injection=sql if sql else defaults.sql_injection,
                )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(
                "Failed to load security patterns from settings, using defaults",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

        return defaults

    def compile_command_injection(self) -> Pattern:
        """Compile command injection patterns into a single regex.

        Returns:
            Compiled regex pattern
        """
        return re.compile("|".join(self.command_injection), re.IGNORECASE)

    def compile_path_traversal(self) -> Pattern:
        """Compile path traversal patterns into a single regex.

        Returns:
            Compiled regex pattern
        """
        return re.compile("|".join(self.path_traversal), re.IGNORECASE)

    def compile_sql_injection(self) -> Pattern:
        """Compile SQL injection patterns into a single regex.

        Returns:
            Compiled regex pattern
        """
        return re.compile("|".join(self.sql_injection), re.IGNORECASE)


class InputValidator:
    """Validates and sanitizes user inputs for security.

    This validator can be used in two ways:
    1. Instance with defaults: validator = InputValidator() - uses default patterns
    2. Instance with custom patterns: validator = InputValidator(security_patterns) - uses custom patterns

    Example with custom patterns from settings:
        from prdiffer.infrastructure.settings import get_settings_service
        from prdiffer.infrastructure.security.input_validator import InputValidator, SecurityPatterns

        settings = get_settings_service()
        patterns = SecurityPatterns.from_settings(settings)
        validator = InputValidator(security_patterns=patterns)
        owner, repo, pr = validator.validate_github_url(url)
    """

    # Class-level patterns (fallback when settings not available)
    _COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"`",  # Backticks
    ]

    _PATH_TRAVERSAL_PATTERNS = [
        r"\.\.",  # Parent directory (Unix)
        r"~/",  # Home directory (Unix)
        r"/etc/",  # System directories (Unix)
        r"/var/",
        r"/usr/",
        r"[a-zA-Z]:\\",  # Windows absolute paths
        r"\.\.\\",  # Windows parent directory
        r"\\\\",  # UNC paths
    ]

    _SQL_INJECTION_PATTERNS = [
        r"(?:--|#|/\*|\*/)",  # SQL comments
        r"\b(?:union|select|insert|update|delete|drop|create|alter)\b",  # SQL keywords
        r"(?:exec|execute|xp_)",  # Stored procedures
    ]

    # Pre-compiled combined patterns for performance (Task 3.4)
    _COMMAND_INJECTION_COMPILED = re.compile(r"[;&|`$]|\$\(|`", re.IGNORECASE)
    _PATH_TRAVERSAL_COMPILED = re.compile(
        r"\.\.|~/|/etc/|/var/|/usr/|[a-zA-Z]:\\|\.\\|\\\\", re.IGNORECASE
    )
    _SQL_INJECTION_COMPILED = re.compile(
        r"(?:--|#|/\*|\*/)|\b(?:union|select|insert|update|delete|drop|create|alter)\b|(?:exec|execute|xp_)",
        re.IGNORECASE,
    )

    # Regex patterns for validation
    GITHUB_URL_PATTERN: Pattern = re.compile(
        r"^https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9._-]+)/pull/(\d+)/?$"
    )
    GITHUB_REPO_PATTERN: Pattern = re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+$")
    SAFE_USERNAME_PATTERN: Pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    SAFE_REPO_NAME_PATTERN: Pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
    # Git branch/reference name validation
    # Based on Git ref naming rules:
    # - Can contain alphanumeric, hyphens, underscores, dots, and forward slashes
    # - Cannot start or end with slash
    # - Cannot have consecutive slashes
    # - Cannot start with dot
    # - Max length for Git refs is typically around 255 characters
    BRANCH_NAME_PATTERN: Pattern = re.compile(
        r"^[a-zA-Z0-9]([a-zA-Z0-9_\-./]*[a-zA-Z0-9])?$"
    )

    def __init__(self, security_patterns: SecurityPatterns | None = None):
        """Initialize the InputValidator with optional custom security patterns.

        Args:
            security_patterns: Optional SecurityPatterns instance for custom pattern matching.
                If None, uses default class-level patterns.

        Example:
            >>> # Use default patterns
            >>> validator = InputValidator()

            >>> # Use custom patterns from settings
            >>> from prdiffer.infrastructure.settings import get_settings_service
            >>> settings = get_settings_service()
            >>> patterns = SecurityPatterns.from_settings(settings)
            >>> validator = InputValidator(security_patterns=patterns)
        """
        self._security_patterns = security_patterns
        if security_patterns is not None:
            # Compile custom patterns for instance use
            self._command_injection_compiled = (
                security_patterns.compile_command_injection()
            )
            self._path_traversal_compiled = security_patterns.compile_path_traversal()
            self._sql_injection_compiled = security_patterns.compile_sql_injection()
        else:
            # Use class-level compiled patterns (will be accessed via class in methods)
            self._command_injection_compiled = None
            self._path_traversal_compiled = None
            self._sql_injection_compiled = None

    def validate_github_url(self, url: str) -> tuple[str, str, int]:
        """Validate and parse a GitHub PR URL.

        Args:
            url: GitHub PR URL to validate

        Returns:
            Tuple of (owner, repo, pr_number)

        Raises:
            InvalidURLError: If URL is invalid or malicious
        """
        from prdiffer.infrastructure.utils.url_parser import parse_github_pr_url

        if not isinstance(url, str):
            raise InvalidURLError(f"URL must be a string, got {type(url).__name__}")

        url = url.strip()
        if not url:
            raise InvalidURLError("URL cannot be empty")

        # Check for suspicious patterns before parsing
        if self._check_suspicious_patterns_instance(url):
            raise SuspiciousOperationError(
                "URL contains suspicious patterns", details={"url": url[:100]}
            )

        # Delegate parsing and structural validation to URL parser
        return parse_github_pr_url(url)

    @classmethod
    def validate_repository_identifier(cls, identifier: str) -> tuple[str, str]:
        """Validate a repository identifier (owner/repo format).

        Args:
            identifier: Repository identifier to validate

        Returns:
            Tuple of (owner, repo)

        Raises:
            InvalidRepositoryError: If identifier is invalid
        """
        if not identifier:
            raise InvalidRepositoryError("Repository identifier cannot be empty")

        if len(identifier) > 200:
            raise InvalidRepositoryError("Repository identifier too long")

        match = cls.GITHUB_REPO_PATTERN.match(identifier)
        if not match:
            raise InvalidRepositoryError(
                "Invalid repository format. Expected: owner/repo",
                details={"identifier": identifier},
            )

        parts = identifier.split("/")
        if len(parts) != 2:
            raise InvalidRepositoryError("Repository must be in format: owner/repo")

        owner, repo = parts
        cls._validate_github_owner(owner)
        cls._validate_repo_name(repo)

        return owner, repo

    @classmethod
    def _validate_github_owner(cls, owner: str):
        """Validate GitHub username/organization name.

        Args:
            owner: Username to validate

        Raises:
            InvalidRepositoryError: If owner is invalid
        """
        if not owner:
            raise InvalidRepositoryError("Owner cannot be empty")

        if len(owner) > 39:  # GitHub's max username length
            raise InvalidRepositoryError("Owner name too long (max 39 characters)")

        if not cls.SAFE_USERNAME_PATTERN.match(owner):
            raise InvalidRepositoryError(
                "Owner contains invalid characters (allowed: a-z, A-Z, 0-9, -, _)",
                details={"owner": owner},
            )

    @classmethod
    def _validate_repo_name(cls, repo: str):
        """Validate repository name.

        Args:
            repo: Repository name to validate

        Raises:
            InvalidRepositoryError: If repo name is invalid
        """
        if not repo:
            raise InvalidRepositoryError("Repository name cannot be empty")

        if len(repo) > 100:  # GitHub's max repo name length
            raise InvalidRepositoryError(
                "Repository name too long (max 100 characters)"
            )

        if not cls.SAFE_REPO_NAME_PATTERN.match(repo):
            raise InvalidRepositoryError(
                "Repository name contains invalid characters", details={"repo": repo}
            )

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize a string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            InputSanitizationError: If input is suspicious
        """
        if not isinstance(value, str):
            raise InputSanitizationError(f"Expected string, got {type(value)}")

        # Check length
        if len(value) > max_length:
            raise InputSanitizationError(
                f"String too long (max {max_length} characters)"
            )

        # Check for null bytes
        if "\x00" in value:
            raise InputSanitizationError("String contains null bytes")

        # Check for suspicious patterns
        # Use global validator for backward compatibility with classmethod
        if _validator._check_suspicious_patterns_instance(value):
            raise SuspiciousOperationError("String contains suspicious patterns")

        # Remove control characters except common whitespace
        sanitized = "".join(
            char for char in value if char in "\t\n\r" or not (0 <= ord(char) < 32)
        )

        return sanitized

    @classmethod
    def validate_pr_number(cls, pr_number: int) -> int:
        """Validate a PR number.

        Args:
            pr_number: PR number to validate

        Returns:
            Validated PR number

        Raises:
            InvalidPRNumberError: If PR number is invalid
        """
        if not isinstance(pr_number, int):
            raise InvalidPRNumberError(
                f"PR number must be integer, got {type(pr_number)}"
            )

        if pr_number <= 0:
            raise InvalidPRNumberError("PR number must be positive")

        if pr_number > 1000000:
            raise InvalidPRNumberError("PR number too large (max 1000000)")

        return pr_number

    @classmethod
    def validate_file_path(cls, file_path: str) -> str:
        """Validate a file path for cache keys, storage, and other safe operations.

        This validation prevents:
        - Path traversal attacks (../../etc/passwd)
        - Absolute paths being used where relative paths expected
        - Excessively long paths that could cause issues
        - Suspicious patterns that could indicate injection attempts

        Args:
            file_path: File path to validate

        Returns:
            Validated file path

        Raises:
            InputSanitizationError: If path is invalid
            SuspiciousOperationError: If path contains suspicious patterns

        Examples:
            >>> validate_file_path("cache/pr_123.json")
            'cache/pr_123.json'
            >>> validate_file_path("data/backup.tar.gz")
            'data/backup.tar.gz'
        """
        if not isinstance(file_path, str):
            raise InputSanitizationError("File path must be a string")

        if not file_path:
            raise InputSanitizationError("File path cannot be empty")

        # Normalize the path to prevent bypass attempts with ./ or extra slashes
        file_path = file_path.replace("\\", "/")  # Normalize Windows paths
        while "//" in file_path:
            file_path = file_path.replace("//", "/")

        # Check length limits
        if len(file_path) > 500:
            raise InputSanitizationError("File path too long (max 500 characters)")

        # Check for path traversal using pre-compiled pattern
        if cls._PATH_TRAVERSAL_COMPILED.search(file_path):
            raise SuspiciousOperationError(
                "File path contains path traversal patterns",
                details={"path": file_path[:100]},
            )

        # Ensure path doesn't start with / (absolute path)
        if file_path.startswith("/"):
            raise InputSanitizationError(
                "Absolute paths not allowed (use relative paths)",
                details={"path": file_path[:50]},
            )

        # Check for suspicious patterns in file extensions
        # Warn about potentially dangerous file extensions
        dangerous_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".scr",  # Executables
            ".sh",
            ".bash",
            ".zsh",
            ".ps1",
            ".psm1",  # Scripts
            ".dll",
            ".so",
            ".dylib",  # Libraries
        ]
        file_ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if file_ext in dangerous_extensions:
            # Log warning but allow - could be legitimate in some contexts
            pass  # Could add logging here if needed

        return file_path

    @classmethod
    def validate_token(cls, token: str) -> str:
        """Validate an authentication token format.

        Args:
            token: Token to validate

        Returns:
            Validated token

        Raises:
            InputSanitizationError: If token format is invalid
        """
        if not isinstance(token, str):
            raise InputSanitizationError("Token must be a string")

        if not token:
            raise InputSanitizationError("Token cannot be empty")

        if len(token) < 20:
            raise InputSanitizationError("Token too short (minimum 20 characters)")

        if len(token) > 500:
            raise InputSanitizationError("Token too long (maximum 500 characters)")

        # Check for whitespace
        if token != token.strip():
            raise InputSanitizationError("Token contains leading/trailing whitespace")

        # Token should be alphanumeric with some special chars
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", token):
            raise InputSanitizationError("Token contains invalid characters")

        return token

    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        """Validate a user ID.

        Args:
            user_id: User ID to validate

        Returns:
            Validated user ID

        Raises:
            InputSanitizationError: If user ID is invalid
        """
        if not isinstance(user_id, str):
            raise InputSanitizationError("User ID must be a string")

        if not user_id:
            raise InputSanitizationError("User ID cannot be empty")

        if len(user_id) > 100:
            raise InputSanitizationError("User ID too long (max 100 characters)")

        # Allow alphanumeric, hyphens, underscores, @, and dots
        if not re.match(r"^[a-zA-Z0-9_\-@\.]+$", user_id):
            raise InputSanitizationError(
                "User ID contains invalid characters", details={"user_id": user_id[:50]}
            )

        return user_id

    @classmethod
    def validate_branch_name(cls, branch: str) -> str:
        """Validate a Git branch or reference name.

        Args:
            branch: Branch or reference name to validate

        Returns:
            Validated branch name

        Raises:
            InputSanitizationError: If branch name is invalid
        """
        if not isinstance(branch, str):
            raise InputSanitizationError("Branch name must be a string")

        if not branch:
            raise InputSanitizationError("Branch name cannot be empty")

        if len(branch) > 255:
            raise InputSanitizationError("Branch name too long (max 255 characters)")

        # Check for suspicious patterns
        # Use global validator for backward compatibility with classmethod
        if _validator._check_suspicious_patterns_instance(branch):
            raise SuspiciousOperationError(
                "Branch name contains suspicious patterns",
                details={"branch": branch[:100]},
            )

        # Validate against Git branch naming rules
        if not cls.BRANCH_NAME_PATTERN.match(branch):
            raise InputSanitizationError(
                "Branch name contains invalid characters or format",
                details={
                    "branch": branch[:100],
                    "allowed": "alphanumeric, hyphens, underscores, dots, and forward slashes",
                },
            )

        # Additional checks for branch name safety
        # Cannot start or end with slash
        if branch.startswith("/") or branch.endswith("/"):
            raise InputSanitizationError("Branch name cannot start or end with '/'")

        # Cannot have consecutive slashes
        if "//" in branch:
            raise InputSanitizationError(
                "Branch name cannot contain consecutive slashes"
            )

        # Cannot start with dot (hidden file/path)
        if branch.startswith("."):
            raise InputSanitizationError("Branch name cannot start with '.'")

        # Cannot contain ".." (parent directory reference)
        if ".." in branch:
            raise SuspiciousOperationError("Branch name cannot contain '..'")

        return branch

    def _check_suspicious_patterns_instance(self, value: str) -> bool:
        """Instance method for checking suspicious patterns.

        Uses instance-level custom patterns if available, otherwise falls back
        to class-level default patterns for performance (Task 3.4).

        Args:
            value: Value to check

        Returns:
            True if suspicious patterns found
        """
        # Use instance patterns if available (custom SecurityPatterns)
        if self._security_patterns is not None:
            # When security_patterns is not None, compiled patterns are guaranteed to be set
            assert self._command_injection_compiled is not None
            assert self._path_traversal_compiled is not None
            assert self._sql_injection_compiled is not None

            if self._command_injection_compiled.search(value):
                return True
            if self._path_traversal_compiled.search(value):
                return True
            if self._sql_injection_compiled.search(value):
                return True
            return False

        # Fall back to class-level default patterns
        if self._COMMAND_INJECTION_COMPILED.search(value):
            return True
        if self._PATH_TRAVERSAL_COMPILED.search(value):
            return True
        if self._SQL_INJECTION_COMPILED.search(value):
            return True
        return False

    @classmethod
    def _contains_suspicious_patterns(cls, value: str) -> bool:
        """Check if value contains suspicious patterns (classmethod for backward compatibility).

        This method provides backward compatibility for tests and code that call
        this method as a classmethod. For new code with custom patterns,
        create an instance with SecurityPatterns and call _check_suspicious_patterns_instance.

        Args:
            value: Value to check

        Returns:
            True if suspicious patterns found
        """
        # Use the global validator instance for classmethod calls
        return _validator._check_suspicious_patterns_instance(value)

    @classmethod
    def sanitize_for_logging(cls, value: str, max_length: int = 200) -> str:
        """Sanitize a value for safe logging.

        Args:
            value: Value to sanitize
            max_length: Maximum length for logged value

        Returns:
            Sanitized value safe for logging
        """
        if not isinstance(value, str):
            value = str(value)

        # Truncate long values
        if len(value) > max_length:
            value = value[:max_length] + "..."

        # Remove control characters
        sanitized = "".join(
            char if char.isprintable() or char in "\t\n\r" else "?" for char in value
        )

        return sanitized


# Global instance for convenience
_validator = InputValidator()


def validate_github_url(url: str) -> tuple[str, str, int]:
    """Convenience function for URL validation."""
    return _validator.validate_github_url(url)


def validate_repository_identifier(identifier: str) -> tuple[str, str]:
    """Convenience function for repository identifier validation."""
    return _validator.validate_repository_identifier(identifier)


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Convenience function for string sanitization."""
    return _validator.sanitize_string(value, max_length)


def validate_token(token: str) -> str:
    """Convenience function for token validation."""
    return _validator.validate_token(token)


def validate_user_id(user_id: str) -> str:
    """Convenience function for user ID validation."""
    return _validator.validate_user_id(user_id)


def validate_branch_name(branch: str) -> str:
    """Convenience function for branch/ref name validation."""
    return _validator.validate_branch_name(branch)


def validate_pr_number(pr_number: int) -> int:
    """Convenience function for PR number validation.

    Args:
        pr_number: PR number to validate

    Returns:
        Validated PR number

    Raises:
        InvalidPRNumberError: If PR number is invalid

    Example:
        >>> validate_pr_number(123)
        123
        >>> validate_pr_number(0)  # Raises InvalidPRNumberError
    """
    return _validator.validate_pr_number(pr_number)


def validate_file_path(file_path: str) -> str:
    """Convenience function for file path validation.

    Useful for validating cache keys, file storage paths, and any user-provided
    file paths to prevent path traversal attacks.

    Args:
        file_path: File path to validate

    Returns:
        Validated file path

    Raises:
        InputSanitizationError: If path is invalid
        SuspiciousOperationError: If path contains suspicious patterns

    Example:
        >>> validate_file_path("cache/pr_123.json")
        'cache/pr_123.json'
        >>> validate_file_path("../etc/passwd")  # Raises SuspiciousOperationError
    """
    return _validator.validate_file_path(file_path)
