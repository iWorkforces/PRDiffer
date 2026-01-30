"""Unit tests for PR URL parser utility."""

import pytest

from prdiffer.application.utils.pr_url_parser import parse_pr_url
from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidPRNumberError,
    SuspiciousOperationError,
)
from prdiffer.infrastructure.security.input_validator import InputValidator


@pytest.mark.unit
class TestParsePRURL:
    """Test suite for parse_pr_url() function."""

    def test_valid_pr_url_with_pull(self):
        """Test parsing valid PR URL with 'pull' path."""
        result = parse_pr_url("https://github.com/owner/repo/pull/123")
        assert result == ("owner", "repo", 123)

    def test_valid_pr_url_with_pulls(self):
        """Test parsing valid PR URL with 'pulls' path."""
        result = parse_pr_url("https://github.com/owner/repo/pulls/456")
        assert result == ("owner", "repo", 456)

    def test_valid_pr_url_with_hyphen_in_repo(self):
        """Test parsing PR URL with hyphens in repository name."""
        result = parse_pr_url("https://github.com/owner/my-repo/pull/789")
        assert result == ("owner", "my-repo", 789)

    def test_valid_pr_url_with_underscore_in_repo(self):
        """Test parsing PR URL with underscores in repository name."""
        result = parse_pr_url("https://github.com/owner/my_repo/pull/100")
        assert result == ("owner", "my_repo", 100)

    def test_valid_pr_url_with_period_in_repo(self):
        """Test parsing PR URL with periods in repository name."""
        result = parse_pr_url("https://github.com/owner/my.repo/pull/200")
        assert result == ("owner", "my.repo", 200)

    def test_valid_pr_url_with_trailing_slash(self):
        """Test parsing PR URL with trailing slash."""
        result = parse_pr_url("https://github.com/owner/repo/pull/123/")
        assert result == ("owner", "repo", 123)

    def test_valid_pr_url_with_hyphen_in_owner(self):
        """Test parsing PR URL with hyphens in owner name."""
        result = parse_pr_url("https://github.com/my-org/repo/pull/123")
        assert result == ("my-org", "repo", 123)

    def test_valid_pr_url_with_large_pr_number(self):
        """Test parsing PR URL with large PR number."""
        result = parse_pr_url("https://github.com/owner/repo/pull/999999")
        assert result == ("owner", "repo", 999999)

    def test_pr_url_with_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped."""
        result = parse_pr_url("  https://github.com/owner/repo/pull/123  ")
        assert result == ("owner", "repo", 123)

    def test_invalid_pr_url_none(self):
        """Test that None URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="PR URL cannot be None"):
            parse_pr_url(None)  # type: ignore[arg-type]

    def test_invalid_pr_url_empty_string(self):
        """Test that empty string URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="empty or whitespace-only"):
            parse_pr_url("")

    def test_invalid_pr_url_whitespace_only(self):
        """Test that whitespace-only URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="empty or whitespace-only"):
            parse_pr_url("   ")

    def test_invalid_pr_url_wrong_protocol(self):
        """Test that http:// URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="https://github.com/"):
            parse_pr_url("http://github.com/owner/repo/pull/123")

    def test_invalid_pr_url_missing_pr_segment(self):
        """Test that URL without /pull/ or /pulls/ raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/123")

    def test_invalid_pr_url_missing_pr_number(self):
        """Test that URL missing PR number raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/pull/")

    def test_invalid_pr_url_non_numeric_pr_number(self):
        """Test that URL with non-numeric PR number raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/pull/abc")

    def test_invalid_pr_url_zero_pr_number(self):
        """Test that URL with PR number 0 raises InvalidPRNumberError."""
        with pytest.raises(InvalidPRNumberError, match="must be positive"):
            parse_pr_url("https://github.com/owner/repo/pull/0")

    def test_invalid_pr_url_negative_pr_number(self):
        """Test that URL with negative PR number raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/pull/-1")

    def test_invalid_pr_url_too_large_pr_number(self):
        """Test that URL with PR number > 1,000,000 raises InvalidPRNumberError."""
        with pytest.raises(InvalidPRNumberError, match="too large"):
            parse_pr_url("https://github.com/owner/repo/pull/1000001")

    def test_invalid_pr_url_missing_owner(self):
        """Test that URL missing owner raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com//repo/pull/123")

    def test_invalid_pr_url_missing_repo(self):
        """Test that URL missing repo raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner//pull/123")

    def test_invalid_pr_url_invalid_chars_in_owner(self):
        """Test that URL with invalid characters in owner raises SuspiciousOperationError or InvalidURLError."""
        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url("https://github.com/own$er/repo/pull/123")

    def test_invalid_pr_url_invalid_chars_in_repo(self):
        """Test that URL with invalid characters in repo raises InvalidURLError."""
        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url("https://github.com/owner/re*po/pull/123")

    def test_invalid_pr_url_wrong_domain(self):
        """Test that URL with wrong domain raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="https://github.com/"):
            parse_pr_url("https://gitlab.com/owner/repo/pull/123")

    def test_invalid_pr_url_too_long(self):
        """Test that URL > 2000 characters raises InvalidURLError."""
        long_url = "https://github.com/owner/repo/pull/123" + "a" * 2000
        with pytest.raises(InvalidURLError, match="too long"):
            parse_pr_url(long_url)

    def test_invalid_pr_url_with_suspicious_pattern(self):
        """Test that URL with suspicious patterns raises SuspiciousOperationError."""
        # This will be caught by InputValidator's pattern detection
        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url("https://github.com/owner/repo/pull/123 && rm -rf")

    def test_pr_url_with_custom_input_validator(self):
        """Test that custom InputValidator can be passed."""
        custom_validator = InputValidator()
        result = parse_pr_url(
            "https://github.com/owner/repo/pull/123", custom_validator
        )
        assert result == ("owner", "repo", 123)

    def test_pr_url_with_custom_input_validator_none(self):
        """Test that InputValidator is created when None is passed."""
        result = parse_pr_url("https://github.com/owner/repo/pull/123", None)
        assert result == ("owner", "repo", 123)

    def test_pr_url_with_default_input_validator(self):
        """Test that default InputValidator is created when not provided."""
        result = parse_pr_url("https://github.com/owner/repo/pull/123")
        assert result == ("owner", "repo", 123)

    def test_pr_url_non_string_input(self):
        """Test that non-string input raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="must be a string"):
            parse_pr_url(12345)  # type: ignore[arg-type]

    def test_pr_url_dict_input(self):
        """Test that dict input raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="must be a string"):
            parse_pr_url({"url": "https://github.com/owner/repo/pull/123"})  # type: ignore[arg-type]

    def test_pr_url_list_input(self):
        """Test that list input raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="must be a string"):
            parse_pr_url(["https://github.com/owner/repo/pull/123"])  # type: ignore[arg-type]

    def test_real_world_pr_url(self):
        """Test parsing a real-world GitHub PR URL."""
        result = parse_pr_url("https://github.com/facebook/react/pull/12345")
        assert result == ("facebook", "react", 12345)

    def test_pr_url_with_numeric_owner(self):
        """Test parsing PR URL with numeric characters in owner."""
        result = parse_pr_url("https://github.com/user123/repo/pull/789")
        assert result == ("user123", "repo", 789)

    def test_pr_url_with_numeric_repo(self):
        """Test parsing PR URL with numeric characters in repo."""
        result = parse_pr_url("https://github.com/owner/repo123/pull/456")
        assert result == ("owner", "repo123", 456)

    def test_pr_url_owner_max_length(self):
        """Test parsing PR URL with owner at max length (39 chars)."""
        owner = "a" * 39
        result = parse_pr_url(f"https://github.com/{owner}/repo/pull/123")
        assert result == (owner, "repo", 123)

    def test_pr_url_owner_too_long(self):
        """Test that owner > 39 characters raises InvalidURLError."""
        owner = "a" * 40
        with pytest.raises(InvalidURLError, match="Owner name too long"):
            parse_pr_url(f"https://github.com/{owner}/repo/pull/123")

    def test_pr_url_repo_max_length(self):
        """Test parsing PR URL with repo at max length (100 chars)."""
        repo = "a" * 100
        result = parse_pr_url(f"https://github.com/owner/{repo}/pull/123")
        assert result == ("owner", repo, 123)

    def test_pr_url_repo_too_long(self):
        """Test that repo > 100 characters raises InvalidURLError."""
        repo = "a" * 101
        with pytest.raises(InvalidURLError, match="Repository name too long"):
            parse_pr_url(f"https://github.com/owner/{repo}/pull/123")

    def test_pr_url_empty_owner(self):
        """Test that empty owner raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com//repo/pull/123")

    def test_pr_url_empty_repo(self):
        """Test that empty repo raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner//pull/123")
