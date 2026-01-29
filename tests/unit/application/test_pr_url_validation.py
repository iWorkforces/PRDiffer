"""Unit tests for PR URL validation in application layer."""

from unittest.mock import Mock

import pytest

from prdiffer.application.mcp_server import FastMCPServer
from prdiffer.domain.exceptions import InvalidPRNumberError, InvalidURLError
from prdiffer.infrastructure.security.input_validator import InputValidator


@pytest.fixture()
def server() -> FastMCPServer:
    settings_service = Mock()
    cache_service = Mock()
    repository_cache_service = Mock()
    pr_diff_service = Mock()
    logger = Mock()
    github_repository_class = Mock()
    rate_limiter = Mock()
    metrics_tracker = Mock()
    pr_operation_handler = Mock()
    health_monitor = Mock()
    server_configuration = Mock()
    server_configuration.get_mcp_instructions.return_value = "instructions"
    server_configuration.setup_logging = Mock()
    authentication = Mock()
    input_validator = InputValidator()

    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        pr_diff_service=pr_diff_service,
        logger=logger,
        github_repository_class=github_repository_class,
        rate_limiter=rate_limiter,
        metrics_tracker=metrics_tracker,
        pr_operation_handler=pr_operation_handler,
        health_monitor=health_monitor,
        server_configuration=server_configuration,
        authentication=authentication,
        input_validator=input_validator,
    )


@pytest.mark.unit
class TestPRUrlValidation:
    """Validate PR URL parsing through application server."""

    def test_parse_pr_url_supports_pull_and_pulls(self, server: FastMCPServer) -> None:
        owner, repo, pr_number = server._parse_pr_url(
            "https://github.com/owner/repo/pull/123"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 123

        owner, repo, pr_number = server._parse_pr_url(
            "https://github.com/owner/repo/pulls/456"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 456

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "https://gitlab.com/owner/repo/pull/123",
            "https://github.com/owner/pull/123",
        ],
    )
    def test_parse_pr_url_invalid_format(
        self, server: FastMCPServer, invalid_url: str
    ) -> None:
        with pytest.raises(InvalidURLError):
            server._parse_pr_url(invalid_url)

    def test_parse_pr_url_non_github(self, server: FastMCPServer) -> None:
        with pytest.raises(InvalidURLError):
            server._parse_pr_url("https://example.com/owner/repo/pull/123")

    def test_parse_pr_url_malformed_pr_number(self, server: FastMCPServer) -> None:
        with pytest.raises(InvalidPRNumberError):
            server._parse_pr_url("https://github.com/owner/repo/pull/0")
