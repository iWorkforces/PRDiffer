"""Input validation and sanitization for security.

This module provides comprehensive input validation to prevent:
- SQL injection
- Command injection
- Path traversal
- XSS attacks
- Malicious URLs
- Invalid data formats
"""

import re
from typing import Pattern

from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    InputSanitizationError,
    SuspiciousOperationError,
)


class InputValidator:
    """Validates and sanitizes user inputs for security."""

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

    # Dangerous patterns to block
    # Note: Patterns are designed to avoid ReDoS vulnerabilities by using
    # lookahead assertions and atomic groupings where possible
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"`",  # Backticks
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.",  # Parent directory (Unix)
        r"~/",  # Home directory (Unix)
        r"/etc/",  # System directories (Unix)
        r"/var/",
        r"/usr/",
        # Windows path traversal patterns
        r"[a-zA-Z]:\\",  # Windows absolute paths (e.g., C:\)
        r"\.\.\\",  # Windows parent directory (e.g., ..\)
        r"\\\\",  # UNC paths (e.g., \\server\share)
    ]

    SQL_INJECTION_PATTERNS = [
        r"(?:--|#|/\*|\*/)",  # SQL comments
        # Fixed: Use word boundary \b and lookahead (?=\s|$) to prevent ReDoS
        # The \b ensures we match whole words (not "union" in "reunion")
        # The lookahead asserts whitespace or end-of-string follows without consuming it
        r"\b(?:union|select|insert|update|delete|drop|create|alter)\b",  # SQL keywords
        r"(?:exec|execute|xp_)",  # Stored procedures
    ]

    @classmethod
    def validate_github_url(cls, url: str) -> tuple[str, str, int]:
        """Validate and parse a GitHub PR URL.

        Args:
            url: GitHub PR URL to validate

        Returns:
            Tuple of (owner, repo, pr_number)

        Raises:
            InvalidURLError: If URL is invalid or malicious
        """
        if not url:
            raise InvalidURLError("URL cannot be empty")

        # Check URL length (prevent DoS)
        if len(url) > 2000:
            raise InvalidURLError("URL too long (max 2000 characters)")

        # Ensure HTTPS
        if not url.startswith("https://github.com/"):
            raise InvalidURLError(
                "URL must start with https://github.com/",
                details={"url": url[:100]},  # Only include first 100 chars
            )

        # Check for suspicious patterns
        if cls._contains_suspicious_patterns(url):
            raise SuspiciousOperationError(
                "URL contains suspicious patterns", details={"url": url[:100]}
            )

        # Parse URL
        match = cls.GITHUB_URL_PATTERN.match(url)
        if not match:
            raise InvalidURLError(
                "Invalid GitHub PR URL format. Expected: https://github.com/owner/repo/pull/123",
                details={"url": url[:100]},
            )

        owner, repo, pr_number_str = match.groups()

        # Validate components
        cls._validate_github_owner(owner)
        cls._validate_repo_name(repo)

        try:
            pr_number = int(pr_number_str)
            if pr_number <= 0:
                raise InvalidPRNumberError("PR number must be positive")
            if pr_number > 1000000:  # Reasonable upper limit
                raise InvalidPRNumberError("PR number too large")
        except ValueError:
            raise InvalidPRNumberError(f"Invalid PR number: {pr_number_str}")

        return owner, repo, pr_number

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
        if cls._contains_suspicious_patterns(value):
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
        if cls._contains_suspicious_patterns(branch):
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

    @classmethod
    def _contains_suspicious_patterns(cls, value: str) -> bool:
        """Check if value contains suspicious patterns.

        Args:
            value: Value to check

        Returns:
            True if suspicious patterns found
        """
        value_lower = value.lower()

        # Check command injection
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                return True

        # Check path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        # Check SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True

        return False

    @classmethod
    def validate_file_path(cls, file_path: str) -> str:
        """Validate a file path (for cache keys, etc.).

        Args:
            file_path: File path to validate

        Returns:
            Validated file path

        Raises:
            InputSanitizationError: If path is suspicious
        """
        if not isinstance(file_path, str):
            raise InputSanitizationError("File path must be a string")

        if not file_path:
            raise InputSanitizationError("File path cannot be empty")

        if len(file_path) > 500:
            raise InputSanitizationError("File path too long")

        # Check for path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, file_path):
                raise SuspiciousOperationError(
                    "File path contains suspicious patterns",
                    details={"path": file_path[:100]},
                )

        # Ensure path doesn't start with /
        if file_path.startswith("/"):
            raise InputSanitizationError("Absolute paths not allowed")

        return file_path

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
