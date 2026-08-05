"""Opt-in concurrency defaults and bounded identity tests (Todo 14)."""

from __future__ import annotations

from prdiffer.domain.config.github_config import GitHubConfig
from prdiffer.infrastructure.settings import SettingsService


def test_settings_toml_parallel_flags_default_false() -> None:
    service = SettingsService(settings_files=["settings.toml"])
    service.clear_cache()
    config = service.get_github_config()
    assert config.parallel_file_fetch_enabled is False
    assert config.parallel_head_base_fetch_enabled is False
    assert config.parallel_diff_generation_enabled is False
    assert config.github_worker_capacity == 1


def test_github_config_worker_capacity_opt_in() -> None:
    serialized = GitHubConfig(parallel_file_fetch_enabled=False, max_concurrent=4)
    assert serialized.github_worker_capacity == 1
    bounded = GitHubConfig(parallel_file_fetch_enabled=True, max_concurrent=4)
    assert bounded.github_worker_capacity == 4
