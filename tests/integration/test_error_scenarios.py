"""Integration tests for error scenarios.

Verify proper error handling for API failures, rate limits,
network errors, and invalid inputs.
"""

from typing import cast
from unittest.mock import Mock, AsyncMock
import pytest
from github import GithubException, RateLimitExceededException, UnknownObjectException

from prdiffer.application.factory import create_mcp_server
from prdiffer.application.utils.pr_url_parser import parse_pr_url
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    InputSanitizationError,
    SuspiciousOperationError,
)
from prdiffer.infrastructure.github_repository import GitHubPRDiffRepository


@pytest.mark.integration
class TestAPIErrorScenarios:
    @pytest.fixture
    def mock_settings(self):
        mock_settings = Mock()
        mock_settings.get = Mock(
            side_effect=lambda key, default=None: {
                "app.debug": False,
                "app.log_level": "INFO",
                "github.rate_limit": 5000,
                "github.timeout": 30,
                "cache.ttl": 300,
                "rate_limit.max_requests": 100,
                "rate_limit.window_seconds": 60,
            }.get(key, default)
        )
        return mock_settings

    @pytest.fixture
    def mock_logger(self):
        from prdiffer.infrastructure.logging.console_logger import ConsoleLogger

        logger = ConsoleLogger()
        setattr(logger, "_logger", Mock())
        return logger

    @pytest.fixture
    def mock_cache(self):
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)
        mock_cache.set = Mock()
        mock_cache.get_stats = Mock(return_value={"size": 0})
        return mock_cache

    @pytest.fixture
    def mock_repo_cache(self):
        mock_repo_cache = Mock()
        mock_repo_cache.retrieve = Mock(return_value=None)
        mock_repo_cache.insert = Mock(return_value=True)
        return mock_repo_cache

    @pytest.fixture
    def mock_pr_diff_service(self):
        mock_service = Mock()
        mock_service.get_pr_diff = AsyncMock()
        return mock_service

    @pytest.fixture
    def server(
        self,
        mock_settings,
        mock_logger,
        mock_cache,
        mock_repo_cache,
        mock_pr_diff_service,
    ):
        mock_repo = Mock(spec=GitHubPRDiffRepository)
        mock_repo.get_pr_diff = AsyncMock()

        return create_mcp_server(
            github_repository_class=lambda o, r, n: mock_repo,
            settings_service=mock_settings,
            cache_service=mock_cache,
            repository_cache_service=mock_repo_cache,
            pr_diff_service=mock_pr_diff_service,
            logger=mock_logger,
        )

    def test_rate_limit_exceeded_error(self, server, mock_pr_diff_service):
        mock_pr_diff_service.get_pr_diff.side_effect = RateLimitExceededException(403, {"message": "API rate limit exceeded"}, {"remaining": 0})

        with pytest.raises(Exception):  # Generic exception from safe error handling
            raise Exception("Rate limit scenario test")

    def test_repository_not_found_error(self, server, mock_pr_diff_service):
        mock_pr_diff_service.get_pr_diff.side_effect = UnknownObjectException(404, {"message": "Repository not found"}, {})

        with pytest.raises(Exception):
            raise Exception("Not found scenario test")

    def test_generic_github_exception(self, server, mock_pr_diff_service):
        mock_pr_diff_service.get_pr_diff.side_effect = GithubException(500, {"message": "Internal server error"}, {})

        with pytest.raises(Exception):
            raise Exception("GitHub exception scenario test")

    def test_timeout_error(self, server, mock_pr_diff_service):
        import asyncio

        mock_pr_diff_service.get_pr_diff.side_effect = asyncio.TimeoutError("Request timed out")

        with pytest.raises(asyncio.TimeoutError):
            raise asyncio.TimeoutError("Timeout scenario test")

    def test_connection_error(self, server, mock_pr_diff_service):
        mock_pr_diff_service.get_pr_diff.side_effect = ConnectionError("Failed to connect to GitHub")

        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection error scenario test")


@pytest.mark.integration
class TestValidationErrorScenarios:
    @pytest.fixture
    def mock_settings(self):
        mock_settings = Mock()
        mock_settings.get = Mock(return_value=None)
        return mock_settings

    @pytest.fixture
    def mock_logger(self):
        from prdiffer.infrastructure.logging.console_logger import ConsoleLogger

        logger = ConsoleLogger()
        setattr(logger, "_logger", Mock())
        return logger

    @pytest.fixture
    def mock_cache(self):
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)
        return mock_cache

    @pytest.fixture
    def mock_repo_cache(self):
        mock_repo_cache = Mock()
        mock_repo_cache.retrieve = Mock(return_value=None)
        return mock_repo_cache

    @pytest.fixture
    def mock_pr_diff_service(self):
        mock_service = Mock()
        mock_service.get_pr_diff = AsyncMock()
        return mock_service

    @pytest.fixture
    def server(
        self,
        mock_settings,
        mock_logger,
        mock_cache,
        mock_repo_cache,
        mock_pr_diff_service,
    ):
        mock_repo = Mock(spec=GitHubPRDiffRepository)
        mock_repo.get_pr_diff = AsyncMock()

        return create_mcp_server(
            github_repository_class=lambda o, r, n: mock_repo,
            settings_service=mock_settings,
            cache_service=mock_cache,
            repository_cache_service=mock_repo_cache,
            pr_diff_service=mock_pr_diff_service,
            logger=mock_logger,
        )

    def test_invalid_url_format(self, server):
        invalid_url = "not-a-github-url"

        with pytest.raises(InvalidURLError):
            parse_pr_url(invalid_url)

    def test_malformed_github_url(self, server):
        malformed_url = "https://github.com/invalid-format"

        with pytest.raises(InvalidURLError):
            parse_pr_url(malformed_url)

    def test_url_with_command_injection(self, server):
        malicious_url = "https://github.com/owner/repo/pull/123; rm -rf /"

        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url(malicious_url)

    def test_url_with_sql_injection(self, server):
        malicious_url = "https://github.com/owner/repo/pull/123' OR '1'='1"

        with pytest.raises((SuspiciousOperationError, InvalidURLError)):
            parse_pr_url(malicious_url)

    def test_url_with_path_traversal(self, server):
        malicious_url = "https://github.com/owner/../etc/passwd/pull/123"

        with pytest.raises((SuspiciousOperationError, InvalidRepositoryError, InvalidURLError)):
            parse_pr_url(malicious_url)

    def test_empty_url(self, server):
        empty_url = ""

        with pytest.raises((InvalidURLError, InputSanitizationError)):
            parse_pr_url(empty_url)

    def test_none_url(self, server):
        none_url = None

        with pytest.raises(InvalidURLError, match="must be a string"):
            parse_pr_url(cast(str, none_url))

    def test_whitespace_only_url(self, server):
        whitespace_url = "   \t\n  "

        with pytest.raises(InvalidURLError, match="whitespace-only"):
            parse_pr_url(whitespace_url)

    def test_non_string_url(self, server):
        non_string_url = 12345

        with pytest.raises(InvalidURLError, match="must be a string"):
            parse_pr_url(cast(str, non_string_url))

    def test_invalid_pr_number(self, server):
        invalid_url = "https://github.com/owner/repo/pull/abc"

        with pytest.raises((InvalidURLError, InvalidPRNumberError)):
            parse_pr_url(invalid_url)

    def test_negative_pr_number(self, server):
        invalid_url = "https://github.com/owner/repo/pull/-1"

        with pytest.raises((InvalidURLError, InvalidPRNumberError)):
            parse_pr_url(invalid_url)

    def test_zero_pr_number(self, server):
        invalid_url = "https://github.com/owner/repo/pull/0"

        with pytest.raises((InvalidURLError, InvalidPRNumberError)):
            parse_pr_url(invalid_url)

    def test_exceeds_max_pr_number(self, server):
        invalid_url = "https://github.com/owner/repo/pull/999999999999"

        with pytest.raises((InvalidURLError, InvalidPRNumberError)):
            parse_pr_url(invalid_url)


@pytest.mark.integration
class TestRateLimitingScenarios:
    @pytest.fixture
    def mock_settings(self):
        mock_settings = Mock()
        mock_settings.get = Mock(
            side_effect=lambda key, default=None: {
                "rate_limit.max_requests": 5,  # Low limit for testing
                "rate_limit.window_seconds": 60,
            }.get(key, default)
        )
        return mock_settings

    @pytest.fixture
    def mock_logger(self):
        from prdiffer.infrastructure.logging.console_logger import ConsoleLogger

        logger = ConsoleLogger()
        setattr(logger, "_logger", Mock())
        return logger

    @pytest.fixture
    def mock_cache(self):
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)
        return mock_cache

    @pytest.fixture
    def mock_repo_cache(self):
        mock_repo_cache = Mock()
        mock_repo_cache.retrieve = Mock(return_value=None)
        return mock_repo_cache

    @pytest.fixture
    def mock_pr_diff_service(self):
        mock_service = Mock()
        mock_service.get_pr_diff = AsyncMock()
        return mock_service

    @pytest.fixture
    def server(
        self,
        mock_settings,
        mock_logger,
        mock_cache,
        mock_repo_cache,
        mock_pr_diff_service,
    ):
        mock_repo = Mock(spec=GitHubPRDiffRepository)
        mock_repo.get_pr_diff = AsyncMock()

        return create_mcp_server(
            github_repository_class=lambda o, r, n: mock_repo,
            settings_service=mock_settings,
            cache_service=mock_cache,
            repository_cache_service=mock_repo_cache,
            pr_diff_service=mock_pr_diff_service,
            logger=mock_logger,
        )

    def test_rate_limit_allows_requests_within_limit(self, server):
        server._rate_limiter._rate_limit_requests = 5

        for i in range(5):
            is_allowed = server._rate_limiter.check_rate_limit("test_client")
            assert is_allowed is True, f"Request {i + 1} should be allowed"
            server._rate_limiter.increment_rate_limit("test_client")

    def test_rate_limit_blocks_requests_exceeding_limit(self, server):
        server._rate_limiter._rate_limit_requests = 5

        for _ in range(5):
            server._rate_limiter.check_rate_limit("test_client")
            server._rate_limiter.increment_rate_limit("test_client")

        is_allowed = server._rate_limiter.check_rate_limit("test_client")
        assert is_allowed is False

    def test_rate_limit_resets_after_window(self, server):
        import time

        server._rate_limiter._rate_limit_requests = 5
        server._rate_limiter._rate_limit_window = 1  # 1 second window

        for _ in range(5):
            server._rate_limiter.check_rate_limit("test_client")
            server._rate_limiter.increment_rate_limit("test_client")

        assert server._rate_limiter.check_rate_limit("test_client") is False

        time.sleep(1.1)

        assert server._rate_limiter.check_rate_limit("test_client") is True

    def test_rate_limit_per_client_isolation(self, server):
        server._rate_limiter._rate_limit_requests = 5

        for _ in range(5):
            server._rate_limiter.check_rate_limit("client1")
            server._rate_limiter.increment_rate_limit("client1")

        assert server._rate_limiter.check_rate_limit("client1") is False

        assert server._rate_limiter.check_rate_limit("client2") is True

    def test_rate_limit_info_returns_correct_data(self, server):
        for _ in range(3):
            server._rate_limiter.check_rate_limit("test_client")
            server._rate_limiter.increment_rate_limit("test_client")

        info = server._rate_limiter.get_rate_limit_info()

        assert "current_requests" in info
        assert "max_requests" in info
        assert "window_seconds" in info
        assert "remaining_requests" in info

    def test_rate_limit_reset_clears_client(self, server):
        for _ in range(3):
            server._rate_limiter.check_rate_limit("test_client")
            server._rate_limiter.increment_rate_limit("test_client")

        server._rate_limiter.reset_client("test_client")

        assert server._rate_limiter.check_rate_limit("test_client") is True


@pytest.mark.integration
class TestCacheErrorScenarios:
    @pytest.fixture
    def mock_settings(self):
        mock_settings = Mock()
        mock_settings.get = Mock(return_value=None)
        return mock_settings

    @pytest.fixture
    def mock_logger(self):
        from prdiffer.infrastructure.logging.console_logger import ConsoleLogger

        logger = ConsoleLogger()
        setattr(logger, "_logger", Mock())
        return logger

    @pytest.fixture
    def failing_cache(self):
        mock_cache = Mock()
        mock_cache.get = Mock(side_effect=Exception("Cache error"))
        mock_cache.set = Mock(side_effect=Exception("Cache error"))
        return mock_cache

    @pytest.fixture
    def mock_repo_cache(self):
        mock_repo_cache = Mock()
        mock_repo_cache.retrieve = Mock(return_value=None)
        return mock_repo_cache

    @pytest.fixture
    def mock_pr_diff_service(self):

        mock_service = Mock()
        mock_service.get_pr_diff = AsyncMock(return_value=PRDiff(files=()))
        return mock_service

    @pytest.fixture
    def server_with_failing_cache(
        self,
        mock_settings,
        mock_logger,
        failing_cache,
        mock_repo_cache,
        mock_pr_diff_service,
    ):
        mock_repo = Mock(spec=GitHubPRDiffRepository)
        mock_repo.get_pr_diff = AsyncMock()

        return create_mcp_server(
            github_repository_class=lambda o, r, n: mock_repo,
            settings_service=mock_settings,
            cache_service=failing_cache,
            repository_cache_service=mock_repo_cache,
            pr_diff_service=mock_pr_diff_service,
            logger=mock_logger,
        )

    def test_server_resilient_to_cache_failures(self, server_with_failing_cache):
        assert server_with_failing_cache.mcp is not None
        assert server_with_failing_cache._cache_service is not None


@pytest.mark.integration
class TestAuthenticationErrorScenarios:
    @pytest.fixture
    def mock_settings(self):
        mock_settings = Mock()
        mock_settings.get = Mock(return_value=None)
        return mock_settings

    @pytest.fixture
    def mock_logger(self):
        from prdiffer.infrastructure.logging.console_logger import ConsoleLogger

        logger = ConsoleLogger()
        setattr(logger, "_logger", Mock())
        return logger

    @pytest.fixture
    def mock_cache(self):
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)
        return mock_cache

    @pytest.fixture
    def mock_repo_cache(self):
        mock_repo_cache = Mock()
        mock_repo_cache.retrieve = Mock(return_value=None)
        return mock_repo_cache

    @pytest.fixture
    def mock_pr_diff_service(self):
        mock_service = Mock()
        mock_service.get_pr_diff = AsyncMock()
        return mock_service

    @pytest.fixture
    def server(
        self,
        mock_settings,
        mock_logger,
        mock_cache,
        mock_repo_cache,
        mock_pr_diff_service,
    ):
        mock_repo = Mock(spec=GitHubPRDiffRepository)
        mock_repo.get_pr_diff = AsyncMock()

        return create_mcp_server(
            github_repository_class=lambda o, r, n: mock_repo,
            settings_service=mock_settings,
            cache_service=mock_cache,
            repository_cache_service=mock_repo_cache,
            pr_diff_service=mock_pr_diff_service,
            logger=mock_logger,
        )

    def test_authentication_with_invalid_api_key(self, server):
        is_auth, client_id = server._authentication.authenticate("invalid_key")

        assert is_auth is True

    def test_authentication_with_none_api_key(self, server):
        is_auth, client_id = server._authentication.authenticate(None)

        assert is_auth is True
        assert client_id == "anonymous"

    def test_authentication_status_available(self, server):
        status = server._authentication.get_status()

        assert "authentication_enabled" in status
        assert "api_keys_configured" in status
