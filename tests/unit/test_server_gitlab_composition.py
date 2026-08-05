"""Tests for server GitLab composition via infrastructure factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.infrastructure.factories.infrastructure_factory import InfrastructureFactory
from prdiffer.infrastructure.vcs_providers.gitlab_repository import GitLabVCSRepository


@pytest.mark.unit
class TestGitLabFactoryComposition:
    def test_create_gitlab_session_reader_shares_runtime_limiter(self) -> None:
        factory = InfrastructureFactory()
        with patch("prdiffer.infrastructure.factories.infrastructure_factory.get_settings_service") as get_settings:
            settings = MagicMock()
            settings.get_gitlab_config.return_value = GitLabConfig(max_concurrent=3)
            get_settings.return_value = settings
            reader1 = factory.create_gitlab_session_reader(private_token="t1")
            reader2 = factory.create_gitlab_session_reader(private_token="t1")
        assert isinstance(reader1, GitLabVCSRepository)
        assert isinstance(reader2, GitLabVCSRepository)
        assert reader1._runtime is reader2._runtime
        assert reader1._runtime.limiter is reader2._runtime.limiter

    def test_invalid_config_fails_before_registration(self) -> None:
        factory = InfrastructureFactory()
        with patch("prdiffer.infrastructure.factories.infrastructure_factory.get_settings_service") as get_settings:
            settings = MagicMock()
            settings.get_gitlab_config.side_effect = ValueError("timeout")
            get_settings.return_value = settings
            with pytest.raises(ValueError):
                factory.create_gitlab_session_reader(private_token=None)
