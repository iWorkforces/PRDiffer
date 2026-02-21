"""Injection detection patterns and methods for security.

This module provides comprehensive injection detection to prevent:
- SQL injection
- Command injection
- Path traversal
- Malicious patterns

Patterns can be loaded from settings or use default values.
"""

import logging
import re
from dataclasses import dataclass
from typing import Pattern, TYPE_CHECKING

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
    def from_settings(cls, settings_service: "SettingsService | None") -> "SecurityPatterns":
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
                    command_injection=command if command else defaults.command_injection,
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


class InjectionDetector:
    """Detects injection patterns in input strings.

    This detector can be used in two ways:
    1. Instance with defaults: detector = InjectionDetector() - uses default patterns
    2. Instance with custom patterns: detector = InjectionDetector(security_patterns) - uses custom patterns

    Example with custom patterns from settings:
        from prdiffer.infrastructure.settings import get_settings_service
        from prdiffer.infrastructure.security.injection_detector import InjectionDetector, SecurityPatterns

        settings = get_settings_service()
        patterns = SecurityPatterns.from_settings(settings)
        detector = InjectionDetector(security_patterns=patterns)
        if detector.check_suspicious_patterns(url):
            raise SuspiciousOperationError("Suspicious input detected")
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

    # Pre-compiled combined patterns for performance
    _COMMAND_INJECTION_COMPILED = re.compile(r"[;&|`$]|\$\(|`", re.IGNORECASE)
    _PATH_TRAVERSAL_COMPILED = re.compile(r"\.\.|~/|/etc/|/var/|/usr/|[a-zA-Z]:\\|\.\\|\\\\", re.IGNORECASE)
    _SQL_INJECTION_COMPILED = re.compile(
        r"(?:--|#|/\*|\*/)|\b(?:union|select|insert|update|delete|drop|create|alter)\b|(?:exec|execute|xp_)",
        re.IGNORECASE,
    )

    def __init__(self, security_patterns: SecurityPatterns | None = None):
        """Initialize the InjectionDetector with optional custom security patterns.

        Args:
            security_patterns: Optional SecurityPatterns instance for custom pattern matching.
                If None, uses default class-level patterns.

        Example:
            >>> # Use default patterns
            >>> detector = InjectionDetector()

            >>> # Use custom patterns from settings
            >>> from prdiffer.infrastructure.settings import get_settings_service
            >>> settings = get_settings_service()
            >>> patterns = SecurityPatterns.from_settings(settings)
            >>> detector = InjectionDetector(security_patterns=patterns)
        """
        self._security_patterns = security_patterns
        if security_patterns is not None:
            # Compile custom patterns for instance use
            self._command_injection_compiled = security_patterns.compile_command_injection()
            self._path_traversal_compiled = security_patterns.compile_path_traversal()
            self._sql_injection_compiled = security_patterns.compile_sql_injection()
        else:
            # Use class-level compiled patterns
            self._command_injection_compiled = None
            self._path_traversal_compiled = None
            self._sql_injection_compiled = None

    def check_suspicious_patterns(self, value: str) -> bool:
        """Instance method for checking suspicious patterns.

        Uses instance-level custom patterns if available, otherwise falls back
        to class-level default patterns for performance.

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
    def contains_suspicious_patterns(cls, value: str) -> bool:
        """Check if value contains suspicious patterns (classmethod for backward compatibility).

        This method provides backward compatibility for tests and code that call
        this method as a classmethod. For new code with custom patterns,
        create an instance with SecurityPatterns and call check_suspicious_patterns.

        Args:
            value: Value to check

        Returns:
            True if suspicious patterns found
        """
        # Use the global detector instance for classmethod calls
        return _detector.check_suspicious_patterns(value)


# Global detector instance for convenience
_detector = InjectionDetector()
