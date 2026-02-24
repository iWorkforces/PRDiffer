"""Input sanitization for security.

This module provides sanitization methods to clean user input and prevent
security vulnerabilities in logs and output.
"""

import logging
from typing import TYPE_CHECKING

from prdiffer.domain.exceptions import InputSanitizationError, SuspiciousOperationError

if TYPE_CHECKING:
    from prdiffer.infrastructure.security.injection_detector import InjectionDetector

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitizes input strings for security.

    This class provides methods to sanitize strings for safe use in logging,
    storage, and other contexts where security is critical.

    Usage:
        >>> InputSanitizer.sanitize_string("Hello World")
        'Hello World'
        >>> InputSanitizer.sanitize_for_logging("Long text...", max_length=100)
        'Long text...'
    """

    def __init__(self, detector: "InjectionDetector | None" = None):
        """Initialize InputSanitizer with optional injection detector.

        Args:
            detector: Optional InjectionDetector instance for pattern checking.
                If None, uses global detector instance.
        """
        # Import here to avoid circular dependency
        from prdiffer.infrastructure.security.injection_detector import _detector

        self._detector = detector if detector is not None else _detector

    @classmethod
    def sanitize_string(
        cls,
        value: str,
        max_length: int = 1000,
        detector: "InjectionDetector | None" = None,
    ) -> str:
        """Sanitize a string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            detector: Optional InjectionDetector instance for pattern checking.

        Returns:
            Sanitized string

        Raises:
            InputSanitizationError: If input is suspicious
            SuspiciousOperationError: If suspicious patterns detected
        """
        # Import here to avoid circular dependency
        from prdiffer.infrastructure.security.injection_detector import _detector

        if detector is None:
            detector = _detector

        # Check length
        if len(value) > max_length:
            raise InputSanitizationError(f"String too long (max {max_length} characters)")

        # Check for null bytes
        if "\x00" in value:
            raise InputSanitizationError("String contains null bytes")

        # Check for suspicious patterns
        if detector.check_suspicious_patterns(value):
            raise SuspiciousOperationError("String contains suspicious patterns")

        # Remove control characters except common whitespace
        sanitized = "".join(char for char in value if char in "\t\n\r" or not (0 <= ord(char) < 32))

        return sanitized

    @classmethod
    def sanitize_for_logging(cls, value: str, max_length: int = 200) -> str:
        """Sanitize a value for safe logging.

        Args:
            value: Value to sanitize
            max_length: Maximum length for logged value

        Returns:
            Sanitized value safe for logging
        """
        # Truncate long values
        if len(value) > max_length:
            value = value[:max_length] + "..."

        # Remove control characters
        sanitized = "".join(char if char.isprintable() or char in "\t\n\r" else "?" for char in value)

        return sanitized


# Module-level convenience functions
def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Convenience function for string sanitization.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        InputSanitizationError: If input is suspicious
        SuspiciousOperationError: If suspicious patterns detected

    Example:
        >>> sanitize_string("Hello World")
        'Hello World'
    """
    return InputSanitizer.sanitize_string(value, max_length)


def sanitize_for_logging(value: str, max_length: int = 200) -> str:
    """Convenience function for logging sanitization.

    Args:
        value: Value to sanitize
        max_length: Maximum length for logged value

    Returns:
        Sanitized value safe for logging

    Example:
        >>> sanitize_for_logging("Long text...", max_length=100)
        'Long text...'
    """
    return InputSanitizer.sanitize_for_logging(value, max_length)
