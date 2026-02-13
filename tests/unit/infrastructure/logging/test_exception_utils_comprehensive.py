"""Comprehensive tests for ExceptionSanitizer."""

import pytest
import traceback

from prdiffer.infrastructure.logging.exception_utils import (
    ExceptionSanitizer,
    sanitize_exception_message,
    sanitize_traceback,
    sanitize_exception_for_logging,
    redact_auth_header,
)


class TestExceptionSanitizerPatterns:
    """Tests for sanitization patterns."""

    def test_github_token_patterns_exist(self):
        """Test that GitHub token patterns are defined."""
        assert len(ExceptionSanitizer.GITHUB_TOKEN_PATTERNS) >= 5

    def test_generic_token_patterns_exist(self):
        """Test that generic token patterns are defined."""
        assert len(ExceptionSanitizer.GENERIC_TOKEN_PATTERNS) >= 3

    def test_password_patterns_exist(self):
        """Test that password patterns are defined."""
        assert len(ExceptionSanitizer.PASSWORD_PATTERNS) >= 3


class TestSanitizeExceptionMessage:
    """Tests for sanitize_exception_message method."""

    def test_sanitize_simple_message(self):
        """Test sanitizing a simple message."""
        exception = Exception("Simple error message")

        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert result == "Simple error message"

    def test_sanitize_empty_exception(self):
        """Test sanitizing empty exception."""
        result = ExceptionSanitizer.sanitize_exception_message(None)

        assert result == ""

    def test_sanitize_github_token(self):
        """Test sanitizing GitHub token."""
        exception = Exception(
            "Error with token ghp_1234567890123456789012345678901234567890"
        )

        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert "ghp_1234567890" not in result
        assert "ghp_" in result or "*" in result


        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert "abcdefghijklmnopqrstuvwxyz1234567890" not in result

    def test_sanitize_password(self):
        """Test sanitizing password."""
        exception = Exception('Error with password: "mysecretpassword123"')

        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert "mysecretpassword123" not in result

    def test_sanitize_email(self):
        """Test sanitizing email."""
        exception = Exception("Error for user testuser@example.com")

        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert "testuser" not in result or "***" in result

    def test_sanitize_ip_address(self):
        """Test sanitizing IP address."""
        exception = Exception("Connection from 192.168.1.100")

        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert "192.168.1.100" not in result

    def test_sanitize_api_key_in_url(self):
        """Test sanitizing API key in URL."""
        exception = Exception(
            "Request to https://api.example.com?api_key=secretkey12345678"
        )

        result = ExceptionSanitizer.sanitize_exception_message(exception)

        assert "secretkey12345678" not in result

    def test_truncate_long_message(self):
        """Test truncating long message."""
        long_message = "A" * 1000
        exception = Exception(long_message)

        result = ExceptionSanitizer.sanitize_exception_message(
            exception, max_length=100
        )

        assert len(result) <= 103  # max_length + "..."
        assert result.endswith("...")

    def test_custom_max_length(self):
        """Test custom max length."""
        exception = Exception("A" * 200)

        result = ExceptionSanitizer.sanitize_exception_message(exception, max_length=50)

        assert len(result) <= 53
        assert result.endswith("...")


class TestSanitizeTraceback:
    """Tests for sanitize_traceback method."""

    def test_sanitize_traceback_none(self):
        """Test sanitizing None traceback."""
        result = ExceptionSanitizer.sanitize_traceback(exc_value=None)

        assert result == ""

    def test_sanitize_traceback_simple(self):
        """Test sanitizing simple traceback."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            result = ExceptionSanitizer.sanitize_traceback(exc_value=e)

            assert "ValueError" in result
            assert "Test error" in result

    def test_sanitize_traceback_with_token(self):
        """Test sanitizing traceback with token."""
        try:
            raise ValueError(
                "Error with token ghp_1234567890123456789012345678901234567890"
            )
        except ValueError as e:
            result = ExceptionSanitizer.sanitize_traceback(exc_value=e)

            assert "ghp_1234567890123456789012345678901234567890" not in result


class TestSanitizeExceptionForLogging:
    """Tests for sanitize_exception_for_logging method."""

    def test_sanitize_exception_basic(self):
        """Test basic exception sanitization."""
        exception = ValueError("Test error")

        result = ExceptionSanitizer.sanitize_exception_for_logging(exception)

        assert result["type"] == "ValueError"
        assert result["module"] == "builtins"
        assert result["message"] == "Test error"

    def test_sanitize_exception_with_traceback(self):
        """Test exception sanitization with traceback."""
        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError as e:
            result = ExceptionSanitizer.sanitize_exception_for_logging(
                e, include_traceback=True
            )

            assert result["type"] == "RuntimeError"
            assert "traceback" in result

    def test_sanitize_exception_without_traceback(self):
        """Test exception sanitization without traceback."""
        exception = TypeError("Test type error")

        result = ExceptionSanitizer.sanitize_exception_for_logging(
            exception, include_traceback=False
        )

        assert "traceback" not in result

    def test_sanitize_exception_custom_max_length(self):
        """Test exception sanitization with custom max length."""
        long_message = "A" * 2000
        exception = ValueError(long_message)

        result = ExceptionSanitizer.sanitize_exception_for_logging(
            exception, max_length=100
        )

        assert len(result["message"]) <= 103


class TestRedactAuthHeader:
    """Tests for redact_auth_header method."""

    def test_redact_bearer_token(self):
        """Test redacting Bearer token."""
        header = "Bearer abcdefghijklmnopqrstuvwxyz1234567890"

        result = ExceptionSanitizer.redact_auth_header(header)

        assert "abcdefghijklmnopqrstuvwxyz1234567890" not in result
        assert "Bearer" in result

    def test_redact_bearer_token_short(self):
        """Test redacting short Bearer token."""
        header = "Bearer short"

        result = ExceptionSanitizer.redact_auth_header(header)

        assert result == "Bearer ****"

    def test_redact_basic_auth(self):
        """Test redacting Basic auth."""
        header = "Basic dXNlcjpwYXNzd29yZA=="

        result = ExceptionSanitizer.redact_auth_header(header)

        assert result == "Basic ****"

    def test_redact_token_prefix(self):
        """Test redacting Token prefix."""
        header = "Token abcdefghijklmnopqrstuvwxyz"

        result = ExceptionSanitizer.redact_auth_header(header)

        assert "abcdefghijklmnopqrstuvwxyz" not in result

    def test_redact_apikey_prefix(self):
        """Test redacting ApiKey prefix."""
        header = "apikey mysecretkey12345678"

        result = ExceptionSanitizer.redact_auth_header(header)

        assert "mysecretkey12345678" not in result

    def test_redact_empty_header(self):
        """Test redacting empty header."""
        result = ExceptionSanitizer.redact_auth_header("")

        assert result == ""

    def test_redact_none_header(self):
        """Test redacting None header."""
        result = ExceptionSanitizer.redact_auth_header(None)

        assert result == ""

    def test_redact_unknown_format_long(self):
        """Test redacting unknown format long header."""
        header = "UnknownAuth abcdefghijklmnopqrstuvwxyz1234567890"

        result = ExceptionSanitizer.redact_auth_header(header)

        assert "abcdefghijklmnopqrstuvwxyz1234567890" not in result

    def test_redact_unknown_format_short(self):
        """Test redacting unknown format short header."""
        header = "Short"

        result = ExceptionSanitizer.redact_auth_header(header)

        assert result == "****"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_sanitize_exception_message_func(self):
        """Test sanitize_exception_message function."""
        exception = ValueError("Test error")

        result = sanitize_exception_message(exception)

        assert result == "Test error"

    def test_sanitize_traceback_func(self):
        """Test sanitize_traceback function."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            result = sanitize_traceback(exc_value=e)

            assert "ValueError" in result

    def test_sanitize_exception_for_logging_func(self):
        """Test sanitize_exception_for_logging function."""
        exception = RuntimeError("Test error")

        result = sanitize_exception_for_logging(exception)

        assert result["type"] == "RuntimeError"
        assert result["message"] == "Test error"

    def test_redact_auth_header_func(self):
        """Test redact_auth_header function."""
        header = "Bearer abcdefghijklmnopqrstuvwxyz1234567890"

        result = redact_auth_header(header)

        assert "abcdefghijklmnopqrstuvwxyz1234567890" not in result


class TestSanitizeString:
    """Tests for _sanitize_string method."""

    def test_sanitize_non_string(self):
        """Test sanitizing non-string value."""
        result = ExceptionSanitizer._sanitize_string(12345)

        assert result == "12345"

    def test_sanitize_string_no_changes(self):
        """Test sanitizing string without sensitive data."""
        result = ExceptionSanitizer._sanitize_string("Normal log message")

        assert result == "Normal log message"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_sanitize_nested_exception(self):
        """Test sanitizing exception with nested cause."""
        try:
            try:
                raise ValueError(
                    "Inner error with token ghp_inner12345678901234567890123456789012"
                )
            except ValueError as inner:
                raise RuntimeError("Outer error") from inner
        except RuntimeError as e:
            result = sanitize_exception_for_logging(e)

            assert result["type"] == "RuntimeError"

    def test_sanitize_unicode_message(self):
        """Test sanitizing unicode message."""
        exception = ValueError("エラーメッセージ with 日本語")

        result = sanitize_exception_message(exception)

        assert "エラーメッセージ" in result

    def test_sanitize_multiline_message(self):
        """Test sanitizing multiline message."""
        exception = ValueError("Line 1\nLine 2\nLine 3")

        result = sanitize_exception_message(exception)

        assert "Line 1" in result
        assert "Line 2" in result

    def test_sanitize_message_with_newlines(self):
        """Test message with newlines is handled."""
        message = "Error:\n  - Item 1\n  - Item 2"
        exception = Exception(message)

        result = sanitize_exception_message(exception)

        assert "Error:" in result
