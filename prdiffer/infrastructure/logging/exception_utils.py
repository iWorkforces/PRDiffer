"""Exception sanitization utilities for secure logging.

This module provides utilities for sanitizing exceptions before logging
to prevent exposure of sensitive information like API tokens, passwords,
and other credentials in log files and console output.
"""

import re
import traceback
from typing import Optional, Any
from types import TracebackType


class ExceptionSanitizer:
    """Utility class for sanitizing exceptions before logging.

    This class provides methods to redact sensitive information from
    exceptions, including API tokens, passwords, and other credentials
    that should not appear in logs.
    """

    # Patterns for detecting and redacting sensitive information
    # GitHub personal access token pattern (ghp_, gho_, ghu_, ghs_)
    GITHUB_TOKEN_PATTERNS = [
        r"(ghp_[a-zA-Z0-9]{36})",  # GitHub personal access token
        r"(gho_[a-zA-Z0-9]{36})",  # GitHub OAuth token
        r"(ghu_[a-zA-Z0-9]{36})",  # GitHub user token
        r"(ghs_[a-zA-Z0-9]{36})",  # GitHub server token
        r"(ghr_[a-zA-Z0-9]{36})",  # GitHub refresh token
        r"(github_pat_[a-zA-Z0-9_]{82})",  # GitHub fine-grained token
    ]

    # Generic token patterns (alphanumeric strings that look like tokens)
    GENERIC_TOKEN_PATTERNS = [
        r'(["\']?token["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,})(["\'])',  # token: "xxx" or token='xxx'
        r'(["\']?api_key["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,})(["\'])',  # api_key: "xxx"
        r'(["\']?authorization["\']?\s*[:=]\s*["\'])([a-zA-Z0-9_\-]{20,})(["\'])',  # authorization: "xxx"
        r"(Bearer\s+)([a-zA-Z0-9_\-\.]{20,})",  # Bearer xxx
    ]

    # Password patterns
    PASSWORD_PATTERNS = [
        r'(["\']?password["\']?\s*[:=]\s*["\'])([^"\']{8,})(["\'])',  # password: "xxx"
        r'(["\']?passwd["\']?\s*[:=]\s*["\'])([^"\']{8,})(["\'])',  # passwd: "xxx"
        r'(["\']?pwd["\']?\s*[:=]\s*["\'])([^"\']{8,})(["\'])',  # pwd: "xxx"
    ]

    # Email patterns (partially redact)
    EMAIL_PATTERN = r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"

    # IP address patterns (partially redact)
    IP_PATTERN = r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})"

    # API key/secret in headers or URLs
    API_KEY_IN_URL = r"([&?](api_key|token|access_token|secret|password)[=][^&\s]{8,})"

    @classmethod
    def sanitize_exception_message(
        cls, exception: Exception, max_length: int = 500
    ) -> str:
        """Sanitize an exception message for safe logging.

        Args:
            exception: The exception to sanitize
            max_length: Maximum length of the sanitized message

        Returns:
            Sanitized exception message safe for logging
        """
        if not exception:
            return ""

        # Get the exception message
        message = str(exception)

        # Apply all sanitization patterns
        sanitized = cls._sanitize_string(message)

        # Truncate if necessary
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized

    @classmethod
    def sanitize_traceback(
        cls,
        exc_type: Optional[type] = None,
        exc_value: Optional[BaseException] = None,
        exc_traceback: Optional[TracebackType] = None,
        max_frames: int = 10,
    ) -> str:
        """Sanitize a traceback for safe logging.

        Args:
            exc_type: Exception type
            exc_value: Exception instance
            exc_traceback: Traceback object
            max_frames: Maximum number of stack frames to include

        Returns:
            Sanitized traceback string safe for logging
        """
        if exc_value is None:
            return ""

        # Format the traceback using the exception object
        tb_lines = traceback.format_exception(exc_value)

        # Limit the number of frames
        if len(tb_lines) > max_frames * 2 + 2:  # Approximate lines per frame
            # Keep header and a subset of frames
            header = tb_lines[:2]
            frames = tb_lines[2 : max_frames * 2 + 2]
            tb_lines = header + frames + ["... (truncated)\n"]

        # Sanitize each line
        sanitized_lines = [cls._sanitize_string(line) for line in tb_lines]

        return "".join(sanitized_lines)

    @classmethod
    def sanitize_exception_for_logging(
        cls,
        exception: Exception,
        include_traceback: bool = False,
        max_length: int = 1000,
    ) -> dict[str, Any]:
        """Create a safe logging representation of an exception.

        Args:
            exception: The exception to sanitize
            include_traceback: Whether to include sanitized traceback
            max_length: Maximum length for each field

        Returns:
            Dictionary with sanitized exception information
        """
        exc_type = type(exception)
        exc_value = exception
        exc_traceback = exception.__traceback__

        result = {
            "type": exc_type.__name__,
            "module": exc_type.__module__,
            "message": cls.sanitize_exception_message(exc_value, max_length),
        }

        if include_traceback and exc_traceback is not None:
            result["traceback"] = cls.sanitize_traceback(
                exc_type, exc_value, exc_traceback
            )[:max_length]

        return result

    @classmethod
    def _sanitize_string(cls, value: str) -> str:
        """Apply all sanitization patterns to a string.

        Args:
            value: String to sanitize

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)

        sanitized = value

        # Apply GitHub token redaction
        for pattern in cls.GITHUB_TOKEN_PATTERNS:
            sanitized = re.sub(
                pattern,
                lambda m: (
                    m.group(1)[:8] + "*" * (len(m.group(1)) - 8)
                    if m.group(1)
                    else m.group(0)
                ),
                sanitized,
                flags=re.IGNORECASE,
            )

        # Apply generic token redaction
        for pattern in cls.GENERIC_TOKEN_PATTERNS:
            sanitized = re.sub(
                pattern,
                lambda m: (
                    m.group(1)
                    + m.group(2)[:4]
                    + "*" * (len(m.group(2)) - 4)
                    + m.group(3)
                ),
                sanitized,
                flags=re.IGNORECASE,
            )

        # Apply password redaction
        for pattern in cls.PASSWORD_PATTERNS:
            sanitized = re.sub(
                pattern,
                lambda m: m.group(1) + "*" * 8 + m.group(3),
                sanitized,
                flags=re.IGNORECASE,
            )

        # Partially redact emails (username is ok, domain should be preserved)
        sanitized = re.sub(
            cls.EMAIL_PATTERN,
            lambda m: m.group(1)[:3] + "***@" + m.group(2),
            sanitized,
        )

        # Partially redact IPs (first and last octet)
        sanitized = re.sub(
            cls.IP_PATTERN,
            lambda m: m.group(1) + ".*." + m.group(4),
            sanitized,
        )

        # Redact API keys in URLs/headers
        sanitized = re.sub(
            cls.API_KEY_IN_URL,
            lambda m: m.group(1)[:8] + "***",
            sanitized,
        )

        return sanitized

    @classmethod
    def redact_auth_header(cls, header_value: str) -> str:
        """Redact an Authorization header value.

        Args:
            header_value: Authorization header value

        Returns:
            Redacted header value
        """
        if not header_value:
            return ""

        header_lower = header_value.lower()

        # Bearer token
        if header_lower.startswith("bearer "):
            token = header_value[7:].strip()
            if len(token) > 10:
                return f"Bearer {token[:4]}...{token[-4:]}"
            return "Bearer ****"

        # Basic auth
        if header_lower.startswith("basic "):
            return "Basic ****"

        # Token type patterns
        for prefix in ["token ", "apikey ", "api-key "]:
            if header_lower.startswith(prefix):
                return f"{prefix.title()}****"

        # Fallback: show first and last few chars
        if len(header_value) > 10:
            return f"{header_value[:4]}...{header_value[-4:]}"

        return "****"


# Global instance for convenience
_sanitizer = ExceptionSanitizer()


def sanitize_exception_message(exception: Exception, max_length: int = 500) -> str:
    """Convenience function for sanitizing exception messages.

    Args:
        exception: The exception to sanitize
        max_length: Maximum length of the sanitized message

    Returns:
        Sanitized exception message safe for logging
    """
    return _sanitizer.sanitize_exception_message(exception, max_length)


def sanitize_traceback(
    exc_type: Optional[type] = None,
    exc_value: Optional[BaseException] = None,
    exc_traceback: Optional[TracebackType] = None,
    max_frames: int = 10,
) -> str:
    """Convenience function for sanitizing tracebacks.

    Args:
        exc_type: Exception type (kept for backward compatibility)
        exc_value: Exception instance
        exc_traceback: Traceback object (kept for backward compatibility)
        max_frames: Maximum number of stack frames to include

    Returns:
        Sanitized traceback string safe for logging
    """
    return _sanitizer.sanitize_traceback(exc_value=exc_value, max_frames=max_frames)


def sanitize_exception_for_logging(
    exception: Exception,
    include_traceback: bool = False,
    max_length: int = 1000,
) -> dict[str, Any]:
    """Convenience function for creating safe exception logging representations.

    Args:
        exception: The exception to sanitize
        include_traceback: Whether to include sanitized traceback
        max_length: Maximum length for each field

    Returns:
        Dictionary with sanitized exception information
    """
    return _sanitizer.sanitize_exception_for_logging(
        exception, include_traceback, max_length
    )


def redact_auth_header(header_value: str) -> str:
    """Convenience function for redacting authorization headers.

    Args:
        header_value: Authorization header value

    Returns:
        Redacted header value
    """
    return _sanitizer.redact_auth_header(header_value)
