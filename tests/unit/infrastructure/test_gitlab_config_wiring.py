"""Tests for GitLabConfig wiring through SettingsService and settings.toml."""

from __future__ import annotations

import pytest

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.infrastructure.settings import SettingsService


@pytest.mark.unit
class TestGitLabConfigDefaults:
    def test_dataclass_defaults(self) -> None:
        config = GitLabConfig()
        assert config.timeout == 30
        assert config.pr_diff_request_timeout_seconds == 180.0
        assert config.max_file_size_bytes == 10_485_760
        assert config.max_total_chars == 200_000
        assert config.max_files_allowed == 50
        assert config.max_concurrent == 4
        assert config.max_retries == 3
        assert config.retry_transient_errors is True
        assert config.obey_rate_limit is True


@pytest.mark.unit
class TestSettingsTomlGitLabDefaults:
    def test_real_settings_resolve_gitlab_config(self) -> None:
        service = SettingsService(settings_files=["settings.toml"])
        service.clear_cache()
        config = service.get_gitlab_config()
        assert config.timeout == 30
        assert config.pr_diff_request_timeout_seconds == 180.0
        assert config.max_file_size_bytes == 10_485_760
        assert config.max_total_chars == 200_000
        assert config.max_files_allowed == 50
        assert config.max_concurrent == 4
        assert config.max_retries == 3
        assert config.retry_transient_errors is True
        assert config.obey_rate_limit is True

    def test_gitlab_config_is_cached_and_cleared(self) -> None:
        service = SettingsService(settings_files=["settings.toml"])
        service.clear_cache()
        first = service.get_gitlab_config()
        second = service.get_gitlab_config()
        assert first is second
        service.clear_cache()
        third = service.get_gitlab_config()
        assert third is not first
        assert third == first
