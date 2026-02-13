"""Tests for webhook cache invalidation with HMAC verification."""

import json
import hmac

import pytest
from unittest.mock import Mock, patch, AsyncMock

from prdiffer.application.mcp_server import FastMCPServer


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    mock = Mock()
    mock.invalidate = AsyncMock()
    return mock


@pytest.fixture
def mock_repository_cache_service():
    """Create a mock repository cache service."""
    mock = Mock()
    mock.invalidate = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_settings():
    """Create a mock settings service."""
    mock = Mock()
    mock.get = Mock(return_value="test_webhook_secret")
    return mock


@pytest.fixture
def mcp_server(mock_cache_service, mock_repository_cache_service, mock_settings):
    """Create an MCP server instance with mocked dependencies."""
    mock_pr_diff_service = Mock()
    mock_logger = Mock()
    mock_github_repo_class = Mock()
    mock_rate_limiter = Mock()
    mock_metrics_tracker = Mock()
    mock_pr_operation_handler = Mock()
    mock_health_monitor = Mock()
    mock_server_configuration = Mock()
    mock_server_configuration.setup_logging = Mock()
    mock_server_configuration.get_mcp_instructions = Mock(
        return_value="Test instructions"
    )

    server = FastMCPServer(
        settings_service=mock_settings,
        cache_service=mock_cache_service,
        repository_cache_service=mock_repository_cache_service,
        pr_diff_service=mock_pr_diff_service,
        logger=mock_logger,
        github_repository_class=mock_github_repo_class,
        rate_limiter=mock_rate_limiter,
        metrics_tracker=mock_metrics_tracker,
        pr_operation_handler=mock_pr_operation_handler,
        health_monitor=mock_health_monitor,
        server_configuration=mock_server_configuration,
    )
    return server


@pytest.mark.unit
class TestWebhookCacheInvalidation:
    """Test webhook cache invalidation functionality."""

    @pytest.mark.asyncio
    async def test_webhook_invalidates_pr_on_opened_event(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that PR cache is invalidated on opened event."""

        webhook_secret = "test_webhook_secret"
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "number": 123,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = f"sha256={hmac.new(webhook_secret.encode(), payload_bytes, 'sha256').hexdigest()}"

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, signature, "pull_request"
        )

        assert result["status"] == "success"
        mock_repository_cache_service.invalidate.assert_called_once_with(
            "owner/repo/pr/123"
        )

    @pytest.mark.asyncio
    async def test_webhook_invalidates_pr_on_synchronize_event(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that PR cache is invalidated on synchronize event."""

        webhook_secret = "test_webhook_secret"
        payload = {
            "action": "synchronize",
            "repository": {"full_name": "owner/repo"},
            "number": 456,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = f"sha256={hmac.new(webhook_secret.encode(), payload_bytes, 'sha256').hexdigest()}"

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, signature, "pull_request"
        )

        assert result["status"] == "success"
        mock_repository_cache_service.invalidate.assert_called_once_with(
            "owner/repo/pr/456"
        )

    @pytest.mark.asyncio
    async def test_webhook_invalidates_repo_on_push_event(
        self, mcp_server, mock_cache_service, mock_repository_cache_service
    ):
        """Test that both cache services are invalidated on push event."""

        webhook_secret = "test_webhook_secret"
        payload = {
            "action": "push",
            "repository": {"full_name": "owner/repo"},
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = f"sha256={hmac.new(webhook_secret.encode(), payload_bytes, 'sha256').hexdigest()}"

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, signature, "push"
        )

        assert result["status"] == "success"
        mock_repository_cache_service.invalidate.assert_called_once_with("owner/repo")
        mock_cache_service.invalidate.assert_called_once_with("owner/repo")

    @pytest.mark.asyncio
    async def test_webhook_returns_error_for_missing_secret(
        self, mcp_server, mock_repository_cache_service, mock_settings
    ):
        """Test that webhook returns error when secret not configured."""
        mock_settings.get = Mock(return_value="")
        payload = {"action": "opened", "repository": {"full_name": "owner/repo"}}
        payload_bytes = json.dumps(payload).encode("utf-8")

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, "sha256=valid", "pull_request"
        )

        assert result["status"] == "error"
        assert result["message"] == "Webhook secret not configured"
        mock_repository_cache_service.invalidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_returns_error_for_missing_repository(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that webhook returns error when repository info missing."""

        webhook_secret = "test_webhook_secret"
        payload = {"action": "opened", "repository": {}}
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = f"sha256={hmac.new(webhook_secret.encode(), payload_bytes, 'sha256').hexdigest()}"

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, signature, "pull_request"
        )

        assert result["status"] == "error"
        assert result["message"] in ["Missing repository info", "Invalid signature"]
        mock_repository_cache_service.invalidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_returns_error_for_unsupported_event(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that webhook returns error for unsupported event types."""
        payload = {"action": "unknown_event", "repository": {"full_name": "owner/repo"}}
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = "sha256=valid_signature"

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, signature, "pull_request"
        )

        assert result["status"] == "error"
        assert result["message"] in ["Unsupported event type", "Invalid signature"]
        mock_repository_cache_service.invalidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_validates_hmac_signature(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that webhook validates HMAC signature."""

        webhook_secret = "test_webhook_secret"
        payload_data = {"action": "opened", "repository": {"full_name": "owner/repo"}}
        payload_bytes = json.dumps(payload_data).encode("utf-8")

        expected_signature = f"sha256={hmac.new(webhook_secret.encode(), payload_bytes, 'sha256').hexdigest()}"

        with patch.object(mcp_server, "_settings_service") as mock_settings:
            mock_settings.get = Mock(return_value=webhook_secret)

            result = await mcp_server._webhook_handler.webhook_invalidate_cache(
                payload_bytes, expected_signature, "pull_request"
            )

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_webhook_rejects_invalid_signature(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that webhook rejects invalid HMAC signature."""

        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "number": 123,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        invalid_signature = "sha256=invalid_signature_here"

        result = await mcp_server._webhook_handler.webhook_invalidate_cache(
            payload_bytes, invalid_signature, "pull_request"
        )

        assert result["status"] == "error"
        assert result["message"] == "Invalid signature"
        mock_repository_cache_service.invalidate.assert_not_called()


@pytest.mark.unit
class TestWebhookHTTPHandler:
    """Test webhook HTTP endpoint handler."""

    @pytest.mark.asyncio
    async def test_webhook_http_endpoint_calls_invalidate(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that HTTP endpoint calls invalidate cache method."""

        webhook_secret = "test_webhook_secret"
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "number": 123,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = f"sha256={hmac.new(webhook_secret.encode(), payload_bytes, 'sha256').hexdigest()}"

        mock_request = Mock()
        mock_request.headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "pull_request",
        }
        mock_request.body = AsyncMock(return_value=payload_bytes)

        handler = mcp_server._webhook_handler.get_webhook_handler()
        response = await handler(mock_request)

        assert response.status_code == 200
        mock_repository_cache_service.invalidate.assert_called_once_with(
            "owner/repo/pr/123"
        )

    @pytest.mark.asyncio
    async def test_webhook_http_endpoint_handles_invalid_json(self, mcp_server):
        """Test that HTTP endpoint handles invalid JSON payload."""
        webhook_secret = "test_webhook_secret"
        invalid_payload_bytes = b"invalid json"
        signature = f"sha256={hmac.new(webhook_secret.encode(), invalid_payload_bytes, 'sha256').hexdigest()}"

        mock_request = Mock()
        mock_request.headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "pull_request",
        }
        mock_request.body = AsyncMock(return_value=invalid_payload_bytes)

        handler = mcp_server._webhook_handler.get_webhook_handler()
        response = await handler(mock_request)

        assert response.status_code == 400
        assert "Invalid" in response.body.decode()

    @pytest.mark.asyncio
    async def test_webhook_http_endpoint_handles_exceptions(
        self, mcp_server, mock_repository_cache_service
    ):
        """Test that HTTP endpoint handles general exceptions gracefully."""
        mock_request = Mock()
        mock_request.headers = {
            "X-Hub-Signature-256": "sha256=valid",
            "X-GitHub-Event": "pull_request",
        }
        mock_request.body = AsyncMock(side_effect=Exception("Unexpected error"))

        handler = mcp_server._webhook_handler.get_webhook_handler()
        response = await handler(mock_request)

        assert response.status_code == 500
        assert "Internal server error" in response.body.decode()
        mock_repository_cache_service.invalidate.assert_not_called()
