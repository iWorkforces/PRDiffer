"""Unit tests for approve_pr plugin.

Tests for ApprovePRPlugin which provides MCP tool for PR approval.
"""

from unittest.mock import Mock, AsyncMock
import pytest
from prdiffer.application.plugins.approve_pr_plugin import ApprovePRPlugin
from prdiffer.domain.usecases.pr_approval_usecases import ApprovePRUseCase


@pytest.mark.unit
class TestApprovePRPlugin:
    """Unit tests for ApprovePRPlugin."""

    @pytest.fixture
    def mock_use_case(self):
        """Mock ApprovePRUseCase."""
        use_case = Mock(spec=ApprovePRUseCase)
        use_case.execute = AsyncMock(return_value="Successfully approved PR #123")
        return use_case

    @pytest.fixture
    def plugin(self, mock_use_case):
        """Create plugin with mocked use case."""
        return ApprovePRPlugin(use_case=mock_use_case)

    def test_name_returns_approve_pr(self, plugin):
        """Test plugin name property."""
        assert plugin.name == "approve_pr"

    def test_description_returns_correct_text(self, plugin):
        """Test plugin description property."""
        expected = "Approve a GitHub PR with a compliment comment"
        assert plugin.description == expected

    def test_enabled_returns_true(self, plugin):
        """Test plugin enabled property."""
        assert plugin.enabled is True

    def test_category_returns_pr_operations(self, plugin):
        """Test plugin category property."""
        assert plugin.category == "pr-operations"

    def test_parameters_returns_correct_schema(self, plugin):
        """Test plugin parameters schema."""
        params = plugin.parameters

        assert params["type"] == "object"
        assert "properties" in params
        assert "compliment" in params["properties"]
        assert "pr_url" in params["properties"]
        assert params["properties"]["compliment"]["type"] == "string"
        assert params["properties"]["pr_url"]["type"] == "string"
        assert set(params["required"]) == {"compliment", "pr_url"}

    @pytest.mark.asyncio
    async def test_execute_with_valid_params(self, plugin, mock_use_case):
        """Test execute with valid parameters."""
        # Arrange
        compliment = "Great work!"
        pr_url = "https://github.com/owner/repo/pull/123"
        expected_result = "Successfully approved PR #123"

        # Act
        result = await plugin.execute(compliment=compliment, pr_url=pr_url)

        # Assert
        mock_use_case.execute.assert_called_once_with(
            pr_url=pr_url, compliment=compliment
        )
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_execute_without_compliment_raises_error(self, plugin):
        """Test execute raises error when compliment is missing."""
        # Act & Assert
        with pytest.raises(ValueError, match="compliment is required"):
            await plugin.execute(pr_url="https://github.com/owner/repo/pull/123")

    @pytest.mark.asyncio
    async def test_execute_without_pr_url_raises_error(self, plugin):
        """Test execute raises error when pr_url is missing."""
        # Act & Assert
        with pytest.raises(ValueError, match="pr_url is required"):
            await plugin.execute(compliment="Nice PR!")

    @pytest.mark.asyncio
    async def test_execute_with_empty_compliment_raises_error(self, plugin):
        """Test execute raises error when compliment is empty."""
        # Act & Assert
        with pytest.raises(ValueError, match="compliment is required"):
            await plugin.execute(
                pr_url="https://github.com/owner/repo/pull/123", compliment=""
            )

    @pytest.mark.asyncio
    async def test_execute_with_invalid_compliment_type_raises_error(self, plugin):
        """Test execute raises error when compliment is not a string."""
        # Act & Assert
        with pytest.raises(ValueError, match="must be a string"):
            await plugin.execute(
                compliment=12345, pr_url="https://github.com/owner/repo/pull/123"
            )

    @pytest.mark.asyncio
    async def test_execute_with_invalid_pr_url_type_raises_error(self, plugin):
        """Test execute raises error when pr_url is not a string."""
        # Act & Assert
        with pytest.raises(ValueError, match="must be a string"):
            await plugin.execute(compliment="Nice PR!", pr_url=12345)

    @pytest.mark.asyncio
    async def test_execute_propagates_use_case_error(self, plugin, mock_use_case):
        """Test execute propagates use case errors."""
        # Arrange
        mock_use_case.execute.side_effect = RuntimeError("Service error")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Service error"):
            await plugin.execute(
                compliment="Nice PR!",
                pr_url="https://github.com/owner/repo/pull/123",
            )
