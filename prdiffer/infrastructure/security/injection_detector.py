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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prdiffer.infrastructure.settings import SettingsService

logger = logging.getLogger(__name__)


@dataclass
class SecurityPatterns:
    """Configurable security patterns loaded from settings."""

    command_injection: list[str]
    path_traversal: list[str]
    sql_injection: list[str]

    @classmethod
    def from_settings(cls, settings_service: "SettingsService | None") -> "SecurityPatterns":
        """Load patterns from settings, falling back to defaults."""
        defaults = cls(
            command_injection=[
                r"[;&|`$]",  # Shell metacharacters
                r"\$\(",  # Command substitution
                r"`",  # Backticks
                r"\|&",  # Bash pipe-and
                r"\|\|",  # Logical OR
                r"&&",  # Logical AND
                r"%0[aAdD]",  # URL-encoded newlines (LF, CR)
                r"\\x[0-9a-fA-F]{2}",  # Hex-encoded characters
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
                r"\.\.%2[fF]",  # URL-encoded ../
                r"\.\.%5[cC]",  # URL-encoded ..\
                r"%2[eE]%2[eE]",  # URL-encoded ..
                r"%252[eE]",  # Double URL-encoded .
            ],
            sql_injection=[
                r"(?:--|#|/\*|\*/)",  # SQL comments
                r"\b(?:union|select|insert|update|delete|drop|create|alter)\b",
                r"(?:exec|execute|xp_)",
                r"['\"]\s*(?:OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",  # 'OR 1=1' patterns
                r"['\"]\s*(?:OR|AND)\s+['\"][^'\"]+['\"]?\s*=\s*['\"]",  # 'OR ''=' patterns
                r";\s*(?:DROP|DELETE|TRUNCATE|UPDATE)",  # Statement termination attacks
                r"%",  # Wildcard (can be abused)
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

    def compile_command_injection(self) -> re.Pattern[str]:
        """Compile command injection patterns into a single regex."""
        return re.compile("|".join(self.command_injection), re.IGNORECASE)

    def compile_path_traversal(self) -> re.Pattern[str]:
        """Compile path traversal patterns into a single regex."""
        return re.compile("|".join(self.path_traversal), re.IGNORECASE)

    def compile_sql_injection(self) -> re.Pattern[str]:
        """Compile SQL injection patterns into a single regex."""
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

    _COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"`",  # Backticks
        r"\|&",  # Bash pipe-and
        r"\|\|",  # Logical OR
        r"&&",  # Logical AND
        r"%0[aAdD]",  # URL-encoded newlines (LF, CR)
        r"\\x[0-9a-fA-F]{2}",  # Hex-encoded characters
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
        r"\.\.%2[fF]",  # URL-encoded ../
        r"\.\.%5[cC]",  # URL-encoded ..\
        r"%2[eE]%2[eE]",  # URL-encoded ..
        r"%252[eE]",  # Double URL-encoded .
    ]

    _SQL_INJECTION_PATTERNS = [
        r"(?:--|#|/\*|\*/)",  # SQL comments
        r"\b(?:union|select|insert|update|delete|drop|create|alter)\b",  # SQL keywords
        r"(?:exec|execute|xp_)",  # Stored procedures
        r"['\"]\s*(?:OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",  # 'OR 1=1' patterns
        r"['\"]\s*(?:OR|AND)\s+['\"][^'\"]+['\"]?\s*=\s*['\"]",  # 'OR ''=' patterns
        r";\s*(?:DROP|DELETE|TRUNCATE|UPDATE)",  # Statement termination attacks
        r"%",  # Wildcard (can be abused)
    ]

    _COMMAND_INJECTION_COMPILED = re.compile(
        r"[;&|`$]|\$\(|`|\|&|\|\||&&|%0[aAdD]|\\x[0-9a-fA-F]{2}",
        re.IGNORECASE,
    )
    _PATH_TRAVERSAL_COMPILED = re.compile(
        r"\.\.|~/|/etc/|/var/|/usr/|[a-zA-Z]:\\|\.\\|\\\\|\.\.%2[fF]|\.\.%5[cC]|%2[eE]%2[eE]|%252[eE]",
        re.IGNORECASE,
    )
    _SQL_INJECTION_COMPILED = re.compile(
        r"(?:--|#|/\*|\*/)|\b(?:union|select|insert|update|delete|drop|create|alter)\b|(?:exec|execute|xp_)|['\"]\s*(?:OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|['\"]\s*(?:OR|AND)\s+['\"][^'\"]+['\"]?\s*=\s*['\"]|;\s*(?:DROP|DELETE|TRUNCATE|UPDATE)|%",
        re.IGNORECASE,
    )

    def __init__(self, security_patterns: SecurityPatterns | None = None):
        """Initialize with optional custom security patterns."""
        self._security_patterns = security_patterns
        if security_patterns is not None:
            self._command_injection_compiled = security_patterns.compile_command_injection()
            self._path_traversal_compiled = security_patterns.compile_path_traversal()
            self._sql_injection_compiled = security_patterns.compile_sql_injection()
        else:
            self._command_injection_compiled = None
            self._path_traversal_compiled = None
            self._sql_injection_compiled = None

    def check_suspicious_patterns(self, value: str) -> bool:
        """Check if value contains suspicious injection patterns."""
        if self._security_patterns is not None:
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

        if self._COMMAND_INJECTION_COMPILED.search(value):
            return True
        if self._PATH_TRAVERSAL_COMPILED.search(value):
            return True
        if self._SQL_INJECTION_COMPILED.search(value):
            return True
        return False

    @classmethod
    def contains_suspicious_patterns(cls, value: str) -> bool:
        """Classmethod wrapper using the global detector instance."""
        return _detector.check_suspicious_patterns(value)


_detector = InjectionDetector()
