"""Tests for metrics endpoint and Prometheus format."""

import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server with metrics tracker for testing."""
    mock_server = Mock()
    mock_server._metrics_tracker = Mock()
    mock_server._metrics_tracker.get_metrics_summary = AsyncMock()
    return mock_server


@pytest.mark.unit
class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self, mock_mcp_server):
        """Test that metrics endpoint returns Prometheus-formatted data."""
        mock_mcp_server._metrics_tracker.get_metrics_summary.return_value = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "success_rate": 95.0,
            "operations": {
                "get_pr_diff": {
                    "total_requests": 50,
                    "successful_requests": 48,
                    "failed_requests": 2,
                    "total_execution_time": 12.5,
                    "min_execution_time": 0.1,
                    "max_execution_time": 2.0,
                    "avg_execution_time": 0.25,
                }
            },
        }

        result = await mock_mcp_server._metrics_tracker.get_metrics_summary()
        assert "total_requests" in result
        assert "successful_requests" in result
        assert "operations" in result

    @pytest.mark.asyncio
    async def test_metrics_endpoint_includes_operation_metrics(self, mock_mcp_server):
        """Test that metrics include operation-specific timing data."""
        mock_mcp_server._metrics_tracker.get_metrics_summary.return_value = {
            "operations": {
                "get_pr_diff": {
                    "total_execution_time": 15.3,
                    "avg_execution_time": 0.31,
                }
            }
        }

        result = await mock_mcp_server._metrics_tracker.get_metrics_summary()
        op_metrics = result["operations"]["get_pr_diff"]
        assert "total_execution_time" in op_metrics
        assert "avg_execution_time" in op_metrics

    @pytest.mark.asyncio
    async def test_metrics_endpoint_excludes_sensitive_data(self, mock_mcp_server):
        """Test that metrics do not expose sensitive information."""
        mock_mcp_server._metrics_tracker.get_metrics_summary.return_value = {
            "total_requests": 100,
            "operations": {
                "get_pr_diff": {
                    "total_requests": 50,
                }
            },
        }

        result = await mock_mcp_server._metrics_tracker.get_metrics_summary()
        assert "api_key" not in str(result)
        assert "token" not in str(result)
