from dataclasses import is_dataclass
from collections.abc import Callable
from typing import Any, Protocol

import pytest
from prdiffer.application.utils import pr_url_parser
from prdiffer.application.utils.pr_url_parser import parse_pr_url
from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidPRNumberError,
    SuspiciousOperationError,
)
from prdiffer.infrastructure.security.input_validator import InputValidator


class PRTarget(Protocol):
    provider: str
    repo_owner: str
    repo_name: str
    pr_number: int


@pytest.mark.unit
class TestParsePRURL:
    def test_valid_pr_url_with_pull(self):
        result = parse_pr_url("https://github.com/owner/repo/pull/123")
        assert result == ("owner", "repo", 123)

    def test_valid_pr_url_with_pulls(self):
        result = parse_pr_url("https://github.com/owner/repo/pulls/456")
        assert result == ("owner", "repo", 456)

    def test_valid_pr_url_with_hyphen_in_repo(self):
        result = parse_pr_url("https://github.com/owner/my-repo/pull/789")
        assert result == ("owner", "my-repo", 789)

    def test_valid_pr_url_with_underscore_in_repo(self):
        result = parse_pr_url("https://github.com/owner/my_repo/pull/100")
        assert result == ("owner", "my_repo", 100)

    def test_valid_pr_url_with_period_in_repo(self):
        result = parse_pr_url("https://github.com/owner/my.repo/pull/200")
        assert result == ("owner", "my.repo", 200)

    def test_valid_pr_url_with_trailing_slash(self):
        result = parse_pr_url("https://github.com/owner/repo/pull/123/")
        assert result == ("owner", "repo", 123)

    def test_valid_pr_url_with_hyphen_in_owner(self):
        result = parse_pr_url("https://github.com/my-org/repo/pull/123")
        assert result == ("my-org", "repo", 123)

    def test_valid_pr_url_with_large_pr_number(self):
        result = parse_pr_url("https://github.com/owner/repo/pull/999999")
        assert result == ("owner", "repo", 999999)

    def test_pr_url_with_whitespace_stripping(self):
        result = parse_pr_url("  https://github.com/owner/repo/pull/123  ")
        assert result == ("owner", "repo", 123)

    def test_invalid_pr_url_none(self):
        with pytest.raises(InvalidURLError, match="must be a string"):
            bad_input: Any = None
            parse_pr_url(bad_input)

    def test_invalid_pr_url_empty_string(self):
        with pytest.raises(InvalidURLError, match="empty or whitespace-only"):
            parse_pr_url("")

    def test_invalid_pr_url_whitespace_only(self):
        with pytest.raises(InvalidURLError, match="empty or whitespace-only"):
            parse_pr_url("   ")

    def test_invalid_pr_url_wrong_protocol(self):
        with pytest.raises(InvalidURLError, match="https://github.com/"):
            parse_pr_url("http://github.com/owner/repo/pull/123")

    def test_invalid_pr_url_missing_pr_segment(self):
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/123")

    def test_invalid_pr_url_missing_pr_number(self):
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/pull/")

    def test_invalid_pr_url_non_numeric_pr_number(self):
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/pull/abc")

    def test_invalid_pr_url_zero_pr_number(self):
        with pytest.raises(InvalidPRNumberError, match="must be positive"):
            parse_pr_url("https://github.com/owner/repo/pull/0")

    def test_invalid_pr_url_negative_pr_number(self):
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner/repo/pull/-1")

    def test_invalid_pr_url_too_large_pr_number(self):
        with pytest.raises(InvalidPRNumberError, match="too large"):
            parse_pr_url("https://github.com/owner/repo/pull/1000001")

    def test_invalid_pr_url_missing_owner(self):
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com//repo/pull/123")

    def test_invalid_pr_url_missing_repo(self):
        with pytest.raises(InvalidURLError, match="Invalid GitHub PR URL format"):
            parse_pr_url("https://github.com/owner//pull/123")

    def test_invalid_pr_url_invalid_chars_in_owner(self):
        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url("https://github.com/own$er/repo/pull/123")

    def test_invalid_pr_url_invalid_chars_in_repo(self):
        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url("https://github.com/owner/re*po/pull/123")

    def test_invalid_pr_url_wrong_domain(self):
        with pytest.raises(InvalidURLError, match="https://github.com/"):
            parse_pr_url("https://gitlab.com/owner/repo/pull/123")

    def test_invalid_pr_url_too_long(self):
        long_url = "https://github.com/owner/repo/pull/123" + "a" * 2000
        with pytest.raises(InvalidURLError, match="too long"):
            parse_pr_url(long_url)

    def test_invalid_pr_url_with_suspicious_pattern(self):
        # InputValidator's pattern detection catches suspicious shell commands
        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url("https://github.com/owner/repo/pull/123 && rm -rf")

    def test_pr_url_with_custom_input_validator(self):
        custom_validator = InputValidator()
        result = parse_pr_url("https://github.com/owner/repo/pull/123", custom_validator)
        assert result == ("owner", "repo", 123)

    def test_pr_url_with_custom_input_validator_none(self):
        result = parse_pr_url("https://github.com/owner/repo/pull/123", None)
        assert result == ("owner", "repo", 123)

    def test_pr_url_non_string_input(self):
        with pytest.raises(InvalidURLError, match="must be a string"):
            bad_input: Any = 12345
            parse_pr_url(bad_input)

    def test_pr_url_dict_input(self):
        with pytest.raises(InvalidURLError, match="must be a string"):
            bad_input: Any = {"url": "https://github.com/owner/repo/pull/123"}
            parse_pr_url(bad_input)

    def test_pr_url_list_input(self):
        with pytest.raises(InvalidURLError, match="must be a string"):
            bad_input: Any = ["https://github.com/owner/repo/pull/123"]
            parse_pr_url(bad_input)

    def test_real_world_pr_url(self):
        result = parse_pr_url("https://github.com/facebook/react/pull/12345")
        assert result == ("facebook", "react", 12345)

    def test_pr_url_with_numeric_owner(self):
        result = parse_pr_url("https://github.com/user123/repo/pull/789")
        assert result == ("user123", "repo", 789)

    def test_pr_url_with_numeric_repo(self):
        result = parse_pr_url("https://github.com/owner/repo123/pull/456")
        assert result == ("owner", "repo123", 456)

    def test_pr_url_owner_max_length(self):
        owner = "a" * 39
        result = parse_pr_url(f"https://github.com/{owner}/repo/pull/123")
        assert result == (owner, "repo", 123)

    def test_pr_url_owner_too_long(self):
        owner = "a" * 40
        with pytest.raises(InvalidURLError, match="Owner name too long"):
            parse_pr_url(f"https://github.com/{owner}/repo/pull/123")

    def test_pr_url_repo_max_length(self):
        repo = "a" * 100
        result = parse_pr_url(f"https://github.com/owner/{repo}/pull/123")
        assert result == ("owner", repo, 123)

    def test_pr_url_repo_too_long(self):
        repo = "a" * 101
        with pytest.raises(InvalidURLError, match="Repository name too long"):
            parse_pr_url(f"https://github.com/owner/{repo}/pull/123")


@pytest.mark.unit
class TestParsePRTarget:
    @pytest.mark.parametrize(
        ("url", "provider", "owner", "repository", "number"),
        [
            ("https://github.com/owner/repo/pull/17", "github", "owner", "repo", 17),
            ("https://gitlab.com/owner/repo/-/merge_requests/17", "gitlab", "owner", "repo", 17),
        ],
    )
    def test_parse_pr_target_returns_provider_aware_dataclass(
        self,
        url: str,
        provider: str,
        owner: str,
        repository: str,
        number: int,
    ) -> None:
        # Given
        validator = InputValidator()
        parse_pr_target: Callable[[str, InputValidator], PRTarget] = getattr(pr_url_parser, "parse_pr_target")

        # When
        target = parse_pr_target(url, validator)

        # Then
        assert is_dataclass(type(target))
        assert target.provider == provider
        assert target.repo_owner == owner
        assert target.repo_name == repository
        assert target.pr_number == number
