"""Domain-specific exception hierarchy for PRDiffer.

This module defines custom exceptions for different error scenarios,
providing better error handling and more informative error messages.
"""

from typing import Optional, Any, Dict


class PRDifferException(Exception):
    """Base exception for all PRDiffer errors.

    All custom exceptions in the PRDiffer application should inherit from this
    base class to ensure consistent error handling and logging across the system.
    This exception provides a structured way to pass error context through the
    optional details dictionary.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize PRDifferException with message and optional details.

        Args:
            message (str): Human-readable error message describing what went wrong.
            details (Optional[Dict[str, Any]]): Optional dictionary with additional
                error context for debugging and logging purposes. Defaults to None.
        """
        super().__init__(message)
        self.message = message
        self.details: Dict[str, Any] = details or {}


# ============================================================================
# Authentication & Authorization Exceptions
# ============================================================================


class AuthenticationError(PRDifferException):
    """Raised when authentication fails.

    This exception is raised when the system cannot authenticate a user or
    service, typically due to invalid credentials, missing authentication
    tokens, or authentication service failures.
    """

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when provided token is invalid or malformed.

    This exception occurs when an authentication token fails validation,
    typically due to incorrect format, invalid characters, or structure
    that doesn't meet token specifications.
    """

    pass


class ExpiredTokenError(AuthenticationError):
    """Raised when authentication token has expired."""

    pass


class MissingTokenError(AuthenticationError):
    """Raised when required authentication token is not provided."""

    pass


class AuthorizationError(PRDifferException):
    """Raised when user lacks permission for requested operation."""

    pass


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user has valid auth but lacks specific permissions."""

    pass


# ============================================================================
# Rate Limiting Exceptions
# ============================================================================


class RateLimitError(PRDifferException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with retry information.

        Args:
            message: Error message
            retry_after: Seconds until rate limit resets
            details: Additional context
        """
        super().__init__(message, details)
        self.retry_after = retry_after


class GlobalRateLimitError(RateLimitError):
    """Raised when global server rate limit is exceeded."""

    pass


class UserRateLimitError(RateLimitError):
    """Raised when per-user rate limit is exceeded."""

    pass


# ============================================================================
# Validation Exceptions
# ============================================================================


class ValidationError(PRDifferException):
    """Raised when input validation fails."""

    pass


class InvalidURLError(ValidationError):
    """Raised when provided URL is invalid or malformed."""

    pass


class InvalidRepositoryError(ValidationError):
    """Raised when repository identifier is invalid."""

    pass


class InvalidPRNumberError(ValidationError):
    """Raised when PR number is invalid."""

    pass


class UnsupportedFormatError(ValidationError):
    """Raised when data format is not supported."""

    pass


# ============================================================================
# GitHub API Exceptions
# ============================================================================


class GitHubAPIError(PRDifferException):
    """Base exception for GitHub API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with HTTP status code.

        Args:
            message: Error message
            status_code: HTTP status code from GitHub API
            details: Additional context
        """
        super().__init__(message, details)
        self.status_code = status_code


class RepositoryNotFoundError(GitHubAPIError):
    """Raised when GitHub repository is not found or not accessible."""

    pass


class PRNotFoundError(GitHubAPIError):
    """Raised when pull request is not found."""

    pass


class FileNotFoundError(GitHubAPIError):
    """Raised when file in repository is not found."""

    pass


class GitHubAuthenticationError(GitHubAPIError):
    """Raised when GitHub authentication fails."""

    pass


class GitHubConnectionError(GitHubAPIError):
    """Raised when connection to GitHub fails."""

    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with retry information.

        Args:
            message: Error message
            retry_after: Seconds until rate limit resets
            status_code: HTTP status code from GitHub API
            details: Additional context
        """
        super().__init__(message, status_code, details)
        self.retry_after = retry_after


# ============================================================================
# Cache Exceptions
# ============================================================================


class CacheError(PRDifferException):
    """Base exception for cache-related errors."""

    pass


class CacheInvalidationError(CacheError):
    """Raised when cache invalidation fails."""

    pass


class CacheCorruptionError(CacheError):
    """Raised when cached data is corrupted."""

    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================


class ConfigurationError(PRDifferException):
    """Raised when configuration is invalid or missing."""

    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration value is invalid."""

    pass


class SecretsError(ConfigurationError):
    """Raised when secrets management fails."""

    pass


# ============================================================================
# Processing Exceptions
# ============================================================================


class ProcessingError(PRDifferException):
    """Base exception for data processing errors."""

    pass


class DiffGenerationError(ProcessingError):
    """Raised when diff generation fails."""

    pass


class FileProcessingError(ProcessingError):
    """Raised when file processing fails."""

    pass


class PatternMatchingError(ProcessingError):
    """Raised when pattern matching fails."""

    pass


# ============================================================================
# Resource Exceptions
# ============================================================================


class ResourceError(PRDifferException):
    """Base exception for resource-related errors."""

    pass


class ResourceExhaustedError(ResourceError):
    """Raised when system resources are exhausted."""

    pass


class MemoryLimitError(ResourceError):
    """Raised when memory limit is exceeded."""

    pass


class TimeoutError(ResourceError):
    """Raised when operation times out."""

    pass


# ============================================================================
# Security Exceptions
# ============================================================================


class SecurityError(PRDifferException):
    """Base exception for security-related errors."""

    pass


class SuspiciousOperationError(SecurityError):
    """Raised when suspicious activity is detected."""

    pass


class InputSanitizationError(SecurityError):
    """Raised when input contains potentially malicious content."""

    pass


class SignatureVerificationError(SecurityError):
    """Raised when request signature verification fails."""

    pass


# ============================================================================
# Helper Functions
# ============================================================================


def get_exception_details(exception: Exception) -> Dict[str, Any]:
    """Extract details from an exception for logging.

    Args:
        exception: Exception to extract details from

    Returns:
        Dictionary with exception details
    """
    details: Dict[str, Any] = {
        "type": type(exception).__name__,
        "message": str(exception),
    }

    if isinstance(exception, PRDifferException):
        details["details"] = exception.details

    if isinstance(exception, GitHubAPIError):
        details["status_code"] = exception.status_code

    if isinstance(exception, RateLimitError):
        details["retry_after"] = exception.retry_after

    return details


def wrap_github_exception(exception: Exception) -> GitHubAPIError:
    """Wrap generic exceptions from GitHub library into typed exceptions.

    Args:
        exception: Exception from PyGithub or requests

    Returns:
        Appropriate GitHubAPIError subclass
    """
    error_msg = str(exception).lower()

    if "404" in error_msg or "not found" in error_msg:
        if "repository" in error_msg:
            return RepositoryNotFoundError(str(exception))
        elif "pull" in error_msg or "pr" in error_msg:
            return PRNotFoundError(str(exception))
        else:
            return FileNotFoundError(str(exception))

    if "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg:
        return GitHubAuthenticationError(str(exception))

    if "429" in error_msg or "rate limit" in error_msg:
        return GitHubRateLimitError(
            str(exception),
            retry_after=60,  # Default retry after 60 seconds
        )

    if "timeout" in error_msg or "connection" in error_msg:
        return GitHubConnectionError(str(exception))

    # Default to generic GitHub API error
    return GitHubAPIError(str(exception))
