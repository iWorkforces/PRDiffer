"""Comprehensive tests for injection_detector.py."""

import pytest
import re
from unittest.mock import Mock, patch

from prdiffer.infrastructure.security.injection_detector import (
    SecurityPatterns,
    InjectionDetector,
    _detector,
)


class TestSecurityPatterns:
    """Tests for SecurityPatterns dataclass."""

    def test_create_with_patterns(self):
        """Test creating SecurityPatterns with custom patterns."""
        patterns = SecurityPatterns(
            command_injection=[r"\$\(", r"`"],
            path_traversal=[r"\.\.", r"~/"],
            sql_injection=[r"--", r"UNION"],
        )
        assert patterns.command_injection == [r"\$\(", r"`"]
        assert patterns.path_traversal == [r"\.\.", r"~/"]
        assert patterns.sql_injection == [r"--", r"UNION"]

    def test_from_settings_none(self):
        """Test from_settings with None returns defaults."""
        patterns = SecurityPatterns.from_settings(None)
        assert patterns.command_injection is not None
        assert patterns.path_traversal is not None
        assert patterns.sql_injection is not None

    def test_from_settings_empty_settings(self):
        """Test from_settings with settings that have no patterns."""
        mock_settings = Mock()
        mock_settings.get.return_value = []
        patterns = SecurityPatterns.from_settings(mock_settings)
        assert len(patterns.command_injection) > 0

    def test_from_settings_with_command_patterns(self):
        """Test from_settings loads command injection patterns."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: (
            [r"custom_pattern"] if "command" in key else []
        )
        patterns = SecurityPatterns.from_settings(mock_settings)
        assert r"custom_pattern" in patterns.command_injection

    def test_from_settings_with_path_patterns(self):
        """Test from_settings loads path traversal patterns."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: (
            [r"custom_path"] if "path" in key else []
        )
        patterns = SecurityPatterns.from_settings(mock_settings)
        assert r"custom_path" in patterns.path_traversal

    def test_from_settings_with_sql_patterns(self):
        """Test from_settings loads SQL injection patterns."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: (
            [r"custom_sql"] if "sql" in key else []
        )
        patterns = SecurityPatterns.from_settings(mock_settings)
        assert r"custom_sql" in patterns.sql_injection

    def test_from_settings_exception_falls_back(self):
        """Test from_settings falls back on exception."""
        mock_settings = Mock()
        mock_settings.get.side_effect = KeyError("test")
        patterns = SecurityPatterns.from_settings(mock_settings)
        assert patterns.command_injection is not None

    def test_compile_command_injection(self):
        """Test compiling command injection patterns."""
        patterns = SecurityPatterns(
            command_injection=[r"\$\(", r"`"],
            path_traversal=[],
            sql_injection=[],
        )
        compiled = patterns.compile_command_injection()
        assert compiled.search("$(whoami)") is not None
        assert compiled.search("`id`") is not None

    def test_compile_path_traversal(self):
        """Test compiling path traversal patterns."""
        patterns = SecurityPatterns(
            command_injection=[],
            path_traversal=[r"\.\.", r"~/"],
            sql_injection=[],
        )
        compiled = patterns.compile_path_traversal()
        assert compiled.search("../../../etc/passwd") is not None
        assert compiled.search("~/secret") is not None

    def test_compile_sql_injection(self):
        """Test compiling SQL injection patterns."""
        patterns = SecurityPatterns(
            command_injection=[],
            path_traversal=[],
            sql_injection=[r"--", r"UNION"],
        )
        compiled = patterns.compile_sql_injection()
        assert compiled.search("SELECT * -- comment") is not None
        assert compiled.search("1 UNION SELECT") is not None


class TestInjectionDetectorInit:
    """Tests for InjectionDetector initialization."""

    def test_init_default(self):
        """Test default initialization uses class patterns."""
        detector = InjectionDetector()
        assert detector._security_patterns is None
        assert detector._command_injection_compiled is None

    def test_init_with_custom_patterns(self):
        """Test initialization with custom patterns."""
        patterns = SecurityPatterns(
            command_injection=[r"test"],
            path_traversal=[r"test"],
            sql_injection=[r"test"],
        )
        detector = InjectionDetector(security_patterns=patterns)
        assert detector._security_patterns is patterns
        assert detector._command_injection_compiled is not None

    def test_init_compiles_custom_patterns(self):
        """Test that custom patterns are compiled on init."""
        patterns = SecurityPatterns(
            command_injection=[r"\$\("],
            path_traversal=[r"\.\."],
            sql_injection=[r"--"],
        )
        detector = InjectionDetector(security_patterns=patterns)
        assert detector._command_injection_compiled.search("$(test)") is not None
        assert detector._path_traversal_compiled.search("../test") is not None
        assert detector._sql_injection_compiled.search("-- comment") is not None


class TestCheckSuspiciousPatterns:
    """Tests for check_suspicious_patterns method."""

    def test_clean_input_returns_false(self):
        """Test clean input returns False."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("normal text") is False

    def test_command_injection_detected(self):
        """Test command injection is detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("$(whoami)") is True
        assert detector.check_suspicious_patterns("test; ls") is True
        assert detector.check_suspicious_patterns("test | cat") is True
        assert detector.check_suspicious_patterns("`id`") is True

    def test_path_traversal_detected(self):
        """Test path traversal is detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("../../../etc/passwd") is True
        assert detector.check_suspicious_patterns("~/secret") is True
        assert detector.check_suspicious_patterns("/etc/passwd") is True
        assert detector.check_suspicious_patterns("C:\\Windows") is True

    def test_sql_injection_detected(self):
        """Test SQL injection is detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("SELECT * FROM users") is True
        assert detector.check_suspicious_patterns("1; DROP TABLE users") is True
        assert detector.check_suspicious_patterns("-- comment") is True
        assert detector.check_suspicious_patterns("UNION SELECT") is True

    def test_custom_patterns_used(self):
        """Test custom patterns are used when provided."""
        patterns = SecurityPatterns(
            command_injection=[r"CUSTOM_PATTERN"],
            path_traversal=[r"NEVER_MATCH"],
            sql_injection=[r"NEVER_MATCH"],
        )
        detector = InjectionDetector(security_patterns=patterns)
        assert detector.check_suspicious_patterns("CUSTOM_PATTERN") is True
        assert detector.check_suspicious_patterns("safe input") is False

    def test_empty_string(self):
        """Test empty string returns False."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("") is False


class TestContainsSuspiciousPatterns:
    """Tests for contains_suspicious_patterns classmethod."""

    def test_clean_input_returns_false(self):
        """Test clean input returns False via classmethod."""
        assert InjectionDetector.contains_suspicious_patterns("normal text") is False

    def test_command_injection_via_classmethod(self):
        """Test command injection detected via classmethod."""
        assert InjectionDetector.contains_suspicious_patterns("$(whoami)") is True

    def test_path_traversal_via_classmethod(self):
        """Test path traversal detected via classmethod."""
        assert InjectionDetector.contains_suspicious_patterns("../../../etc") is True

    def test_sql_injection_via_classmethod(self):
        """Test SQL injection detected via classmethod."""
        assert InjectionDetector.contains_suspicious_patterns("SELECT *") is True


class TestGlobalDetector:
    """Tests for global detector instance."""

    def test_global_detector_exists(self):
        """Test global detector instance exists."""
        assert _detector is not None
        assert isinstance(_detector, InjectionDetector)

    def test_global_detector_uses_defaults(self):
        """Test global detector uses default patterns."""
        assert _detector._security_patterns is None


class TestCommandInjectionPatterns:
    """Detailed tests for command injection patterns."""

    def test_shell_metacharacters(self):
        """Test shell metacharacters are detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("test; command") is True
        assert detector.check_suspicious_patterns("test & command") is True
        assert detector.check_suspicious_patterns("test | command") is True
        assert detector.check_suspicious_patterns("test $var") is True

    def test_command_substitution(self):
        """Test command substitution is detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("$(command)") is True

    def test_backticks(self):
        """Test backticks are detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("`command`") is True


class TestPathTraversalPatterns:
    """Detailed tests for path traversal patterns."""

    def test_parent_directory_unix(self):
        """Test Unix parent directory patterns."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("../../../etc/passwd") is True
        assert detector.check_suspicious_patterns("..\\..\\windows") is True

    def test_home_directory(self):
        """Test home directory pattern."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("~/secrets") is True

    def test_system_directories(self):
        """Test system directory patterns."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("/etc/passwd") is True
        assert detector.check_suspicious_patterns("/var/log") is True
        assert detector.check_suspicious_patterns("/usr/bin") is True

    def test_windows_paths(self):
        """Test Windows path patterns."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("C:\\Windows") is True
        assert detector.check_suspicious_patterns("D:\\Data") is True


class TestSQLInjectionPatterns:
    """Detailed tests for SQL injection patterns."""

    def test_sql_comments(self):
        """Test SQL comment patterns."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("-- comment") is True
        assert detector.check_suspicious_patterns("# comment") is True
        assert detector.check_suspicious_patterns("/* comment */") is True

    def test_sql_keywords(self):
        """Test SQL keyword patterns."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("SELECT * FROM users") is True
        assert detector.check_suspicious_patterns("INSERT INTO") is True
        assert detector.check_suspicious_patterns("UPDATE users") is True
        assert detector.check_suspicious_patterns("DELETE FROM") is True
        assert detector.check_suspicious_patterns("DROP TABLE") is True
        assert detector.check_suspicious_patterns("CREATE TABLE") is True
        assert detector.check_suspicious_patterns("ALTER TABLE") is True
        assert detector.check_suspicious_patterns("UNION SELECT") is True

    def test_stored_procedures(self):
        """Test stored procedure patterns."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("EXEC sp_help") is True
        assert detector.check_suspicious_patterns("xp_cmdshell") is True


class TestEdgeCases:
    """Tests for edge cases."""

    def test_partial_sql_keywords_not_detected(self):
        """Test partial SQL keywords are not detected."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("selection") is False
        assert detector.check_suspicious_patterns("insertion") is False
        assert detector.check_suspicious_patterns("universal") is False

    def test_url_with_valid_chars(self):
        """Test valid URLs are not flagged."""
        detector = InjectionDetector()
        result = detector.check_suspicious_patterns(
            "https://github.com/owner/repo/pull/123"
        )
        assert result is False

    def test_mixed_patterns(self):
        """Test input with multiple pattern types."""
        detector = InjectionDetector()
        assert detector.check_suspicious_patterns("$(cmd) and ../etc") is True
