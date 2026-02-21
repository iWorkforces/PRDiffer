"""Unit tests for PR description update use case.

Tests for UpdatePRDescriptionUseCase which orchestrates PR description
updates with repository service.
"""

from unittest.mock import Mock, AsyncMock
import pytest
from prdiffer.domain.usecases.pr_description_usecases import UpdatePRDescriptionUseCase
from prdiffer.domain.exceptions import ValidationError, InvalidURLError
from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface


@pytest.mark.unit
class TestUpdatePRDescriptionUseCase:
    """Unit tests for UpdatePRDescriptionUseCase."""

    @pytest.fixture
    def mock_repository(self):
        """Mock PR diff repository."""
        repository = Mock(spec=PRDiffRepositoryInterface)
        repository.update_pr_description = AsyncMock()
        return repository

    @pytest.fixture
    def mock_logger(self):
        """Mock logger service."""
        logger = Mock(spec=LoggerServiceInterface)
        logger.info = Mock()
        return logger

    @pytest.fixture
    def use_case(self, mock_repository, mock_logger):
        """Create use case with mocked dependencies."""
        return UpdatePRDescriptionUseCase(pr_diff_repository=mock_repository, logger=mock_logger)

    def test_execute_calls_repository_with_correct_params(self, use_case, mock_repository):
        """Test execution delegates to repository with correct parameters."""
        pr_url = "https://github.com/owner/repo/pull/123"
        pr_description = "New PR description text"

        import asyncio

        result = asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

        mock_repository.update_pr_description.assert_called_once_with(
            pr_url=pr_url,
            description=pr_description,
        )
        assert result is not None

    def test_execute_with_empty_pr_url_raises_error(self, use_case):
        """Test execution raises error when PR URL is empty."""
        pr_url = ""
        pr_description = "New description"

        with pytest.raises(InvalidURLError, match="PR URL cannot be empty"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

    def test_execute_with_none_pr_url_raises_error(self, use_case):
        """Test execution raises error when PR URL is None."""
        pr_url = None
        pr_description = "New description"

        with pytest.raises(TypeError):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

    def test_execute_with_empty_description_raises_error(self, use_case):
        """Test execution raises error when description is empty."""
        pr_url = "https://github.com/owner/repo/pull/123"
        pr_description = ""

        with pytest.raises(ValidationError, match="PR description cannot be empty"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

    def test_execute_with_invalid_pr_url_type_raises_error(self, use_case):
        """Test execution raises error when PR URL is not a string."""
        pr_url = 12345
        pr_description = "New description"

        with pytest.raises(TypeError):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

    def test_execute_with_invalid_description_type_raises_error(self, use_case):
        """Test execution raises error when description is not a string."""
        pr_url = "https://github.com/owner/repo/pull/123"
        pr_description = 12345

        with pytest.raises(ValidationError, match="must be a string"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

    def test_execute_logs_on_start(self, use_case, mock_logger):
        """Test execution logs on start."""
        pr_url = "https://github.com/owner/repo/pull/123"
        pr_description = "New description"

        import asyncio

        asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

        assert mock_logger.info.call_count >= 1

    def test_execute_returns_repository_result(self, use_case, mock_repository):
        """Test execution returns result from repository."""
        pr_url = "https://github.com/owner/repo/pull/123"
        pr_description = "New PR description"
        expected_result = "Successfully updated description for PR #123 in owner/repo"
        mock_repository.update_pr_description.return_value = expected_result

        import asyncio

        result = asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))

        assert result == expected_result

    def test_execute_propagates_repository_error(self, use_case, mock_repository):
        """Test execution propagates repository errors."""
        pr_url = "https://github.com/owner/repo/pull/123"
        pr_description = "New description"
        mock_repository.update_pr_description.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, pr_description=pr_description))
