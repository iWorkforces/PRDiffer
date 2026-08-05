"""Tests for GitLabConfig frozen dataclass validation and defaults."""

from __future__ import annotations

import pytest

from prdiffer.domain.config.gitlab_config import (
    DEFAULT_GITLAB_TIMEOUT_SECONDS,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_FILES_ALLOWED,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_TOTAL_CHARS,
    DEFAULT_PR_DIFF_REQUEST_TIMEOUT_SECONDS,
    GitLabConfig,
)


@pytest.mark.unit
class TestGitLabConfigDefaults:
    def test_defaults_match_plan_contract(self) -> None:
        config = GitLabConfig()
        assert config.timeout == DEFAULT_GITLAB_TIMEOUT_SECONDS == 30
        assert config.max_retries == DEFAULT_MAX_RETRIES == 3
        assert config.max_concurrent == DEFAULT_MAX_CONCURRENT == 4
        assert config.retry_transient_errors is True
        assert config.obey_rate_limit is True
        assert config.max_file_size_bytes == DEFAULT_MAX_FILE_SIZE_BYTES == 10_485_760
        assert config.max_files_allowed == DEFAULT_MAX_FILES_ALLOWED == 50
        assert config.max_total_chars == DEFAULT_MAX_TOTAL_CHARS == 200_000
        assert config.pr_diff_request_timeout_seconds == DEFAULT_PR_DIFF_REQUEST_TIMEOUT_SECONDS == 180.0


@pytest.mark.unit
class TestGitLabConfigFrozen:
    def test_cannot_set_attribute(self) -> None:
        config = GitLabConfig()
        with pytest.raises(AttributeError):
            setattr(config, "timeout", 99)

    def test_is_hashable(self) -> None:
        config = GitLabConfig()
        assert isinstance(hash(config), int)


@pytest.mark.unit
class TestGitLabConfigValidation:
    @pytest.mark.parametrize(
        "kwargs,match",
        [
            ({"timeout": 0}, "timeout"),
            ({"timeout": -1}, "timeout"),
            ({"timeout": 180, "pr_diff_request_timeout_seconds": 180}, "strictly less"),
            ({"timeout": 200, "pr_diff_request_timeout_seconds": 180}, "strictly less"),
            ({"max_retries": -1}, "max_retries"),
            ({"max_concurrent": 0}, "max_concurrent"),
            ({"max_concurrent": -2}, "max_concurrent"),
            ({"max_file_size_bytes": 0}, "max_file_size_bytes"),
            ({"max_files_allowed": 0}, "max_files_allowed"),
            ({"max_total_chars": 0}, "max_total_chars"),
            ({"pr_diff_request_timeout_seconds": 0}, "pr_diff_request_timeout_seconds"),
            ({"pr_diff_request_timeout_seconds": -1.0}, "pr_diff_request_timeout_seconds"),
        ],
    )
    def test_invalid_boundaries_raise_value_error(self, kwargs: dict, match: str) -> None:
        with pytest.raises(ValueError, match=match):
            GitLabConfig(**kwargs)

    def test_max_retries_zero_allowed(self) -> None:
        config = GitLabConfig(max_retries=0)
        assert config.max_retries == 0


@pytest.mark.unit
class TestGitLabConfigFromDict:
    def test_from_empty_dict_uses_defaults(self) -> None:
        config = GitLabConfig.from_dict({})
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.obey_rate_limit is True

    def test_from_dict_overrides(self) -> None:
        config = GitLabConfig.from_dict(
            {
                "timeout": 15,
                "max_retries": 1,
                "max_concurrent": 2,
                "max_files_allowed": 10,
            }
        )
        assert config.timeout == 15
        assert config.max_retries == 1
        assert config.max_concurrent == 2
        assert config.max_files_allowed == 10
