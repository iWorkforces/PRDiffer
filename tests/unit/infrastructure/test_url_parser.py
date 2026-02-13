"""Unit tests for GitHub PR URL parser.

Tests for parse_github_pr_url and validate_github_pr_url functions
that extract and validate owner, repository, and PR number from GitHub PR URLs.
"""

import pytest
from prdiffer.infrastructure.utils.url_parser import (
    parse_github_pr_url,
    validate_github_pr_url,
)
from prdiffer.domain.exceptions import InvalidURLError, InvalidPRNumberError


@pytest.mark.unit
class TestUrlParser:
    """Unit tests for GitHub PR URL parsing."""

    # Valid URL tests
    def test_parse_valid_url_with_pull_path(self):
        """Test parsing valid GitHub PR URL with 'pull/' path."""
        url = "https://github.com/owner/repo/pull/123"
        owner, repo, pr_number = parse_github_pr_url(url)

        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 123

    def test_parse_valid_url_with_pulls_path(self):
        """Test parsing valid GitHub PR URL with 'pulls/' path."""
        url = "https://github.com/owner/repo/pulls/456"
        owner, repo, pr_number = parse_github_pr_url(url)

        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 456

    def test_parse_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        url = "https://github.com/owner/repo/pull/789/"
        owner, repo, pr_number = parse_github_pr_url(url)

        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 789

    def test_parse_url_with_hyphens_in_owner(self):
        """Test parsing URL with hyphens in owner name."""
        url = "https://github.com/my-org-name/repo/pull/1"
        owner, repo, pr_number = parse_github_pr_url(url)

        assert owner == "my-org-name"
        assert repo == "repo"
        assert pr_number == 1

    def test_parse_url_with_dots_in_repo_name(self):
        """Test parsing URL with dots in repo name."""
        url = "https://github.com/owner/repo.name.with.dots/pull/42"
        owner, repo, pr_number = parse_github_pr_url(url)

        assert owner == "owner"
        assert repo == "repo.name.with.dots"
        assert pr_number == 42

    def test_parse_url_with_underscore_in_owner(self):
        """Test parsing URL with underscore in owner name."""
        url = "https://github.com/my_org/repo/pull/99"
        owner, repo, pr_number = parse_github_pr_url(url)

        assert owner == "my_org"
        assert repo == "repo"
        assert pr_number == 99

    # Invalid URL format tests
    def test_parse_url_missing_https(self):
        """Test parsing URL without HTTPS."""
        url = "http://github.com/owner/repo/pull/123"

        with pytest.raises(
            InvalidURLError, match="must start with https://github.com/"
        ):
            parse_github_pr_url(url)

    def test_parse_url_missing_github_com(self):
        """Test parsing URL with wrong domain."""
        url = "https://gitlab.com/owner/repo/pull/123"

        with pytest.raises(
            InvalidURLError, match="must start with https://github.com/"
        ):
            parse_github_pr_url(url)

    def test_parse_url_missing_owner(self):
        """Test parsing URL with missing owner."""
        url = "https://github.com//repo/pull/123"

        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)

    def test_parse_url_missing_repo(self):
        """Test parsing URL with missing repo."""
        url = "https://github.com/owner//pull/123"

        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)

    def test_parse_url_missing_pr_number(self):
        """Test parsing URL with missing PR number."""
        url = "https://github.com/owner/repo/pull/"

        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)

    def test_parse_url_with_non_numeric_pr(self):
        """Test parsing URL with non-numeric PR number."""
        url = "https://github.com/owner/repo/pull/abc"

        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)

    def test_parse_url_with_zero_pr_number(self):
        """Test parsing URL with zero PR number."""
        url = "https://github.com/owner/repo/pull/0"

        with pytest.raises(InvalidPRNumberError, match="must be positive"):
            parse_github_pr_url(url)

    def test_parse_url_with_negative_pr_number(self):
        """Test parsing URL with negative PR number."""
        url = "https://github.com/owner/repo/pull/-1"

        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)

    def test_parse_url_with_too_large_pr_number(self):
        """Test parsing URL with excessively large PR number."""
        url = "https://github.com/owner/repo/pull/9999999"

        with pytest.raises(InvalidPRNumberError, match="too large"):
            parse_github_pr_url(url)

    # Edge case tests
    def test_parse_empty_url(self):
        """Test parsing empty URL."""
        url = ""

        with pytest.raises(InvalidURLError, match="cannot be None or empty"):
            parse_github_pr_url(url)

    def test_parse_none_url(self):
        """Test parsing None URL."""
        url = None

        with pytest.raises(InvalidURLError, match="cannot be None or empty"):
            parse_github_pr_url(url)

    def test_parse_whitespace_only_url(self):
        """Test parsing whitespace-only URL."""
        url = "   "

        with pytest.raises(InvalidURLError, match="cannot be empty or whitespace-only"):
            parse_github_pr_url(url)

    def test_parse_url_with_invalid_characters(self):
        """Test parsing URL with invalid characters in owner."""
        url = "https://github.com/owner@bad/repo/pull/123"

        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)

    def test_parse_url_too_long(self):
        """Test parsing URL exceeding maximum length."""
        url = "https://github.com/owner/repo/pull/1" + "a" * 2000

        with pytest.raises(InvalidURLError, match="too long"):
            parse_github_pr_url(url)

    def test_parse_non_string_url(self):
        """Test parsing non-string URL.

        The implementation does not handle non-string input explicitly,
        so it raises AttributeError when trying to call .strip() on an int.
        """
        url = 12345

        with pytest.raises(AttributeError):
            parse_github_pr_url(url)

    # Validation function tests
    def test_validate_valid_url(self):
        """Test validation returns True for valid URL."""
        url = "https://github.com/owner/repo/pull/123"

        assert validate_github_pr_url(url) is True

    def test_validate_url_with_pulls_path(self):
        """Test validation returns True for URL with 'pulls/' path."""
        url = "https://github.com/owner/repo/pulls/456"

        assert validate_github_pr_url(url) is True

    def test_validate_invalid_url_format(self):
        """Test validation returns False for invalid URL format."""
        url = "https://gitlab.com/owner/repo/pull/123"

        assert validate_github_pr_url(url) is False

    def test_validate_url_with_non_numeric_pr(self):
        """Test validation returns False for non-numeric PR number."""
        url = "https://github.com/owner/repo/pull/abc"

        assert validate_github_pr_url(url) is False

    def test_validate_url_with_negative_pr(self):
        """Test validation returns False for negative PR number."""
        url = "https://github.com/owner/repo/pull/-1"

        assert validate_github_pr_url(url) is False

    def test_validate_empty_url(self):
        """Test validation returns False for empty URL."""
        url = ""

        assert validate_github_pr_url(url) is False

    def test_validate_url_with_invalid_characters(self):
        """Test validation returns False for URL with invalid characters."""
        url = "https://github.com/owner@bad/repo/pull/123"

        assert validate_github_pr_url(url) is False
