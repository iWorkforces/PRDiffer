"""Unit tests for PR approval use case.

Tests for ApprovePRUseCase which orchestrates PR approval
with repository service.
"""

from unittest.mock import Mock, AsyncMock
import pytest
from prdiffer.domain.usecases.pr_approval_usecases import ApprovePRUseCase
from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface


@pytest.mark.unit
class TestApprovePRUseCase:
    """Unit tests for ApprovePRUseCase."""

    @pytest.fixture
    def mock_repository(self):
        """Mock PR diff repository."""
        repository = Mock(spec=PRDiffRepositoryInterface)
        repository.approve_pr_with_comment = AsyncMock()
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
        return ApprovePRUseCase(pr_diff_repository=mock_repository, logger=mock_logger)

    def test_execute_calls_repository_with_correct_params(
        self, use_case, mock_repository
    ):
        """Test execution delegates to repository with correct parameters."""
        # Arrange
        pr_url = "https://github.com/owner/repo/pull/123"
        compliment = "Great work on this PR!"

        # Act
        import asyncio

        result = asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

        # Assert
        mock_repository.approve_pr_with_comment.assert_called_once_with(
            pr_url=pr_url,
            compliment=compliment,
        )
        assert "Successfully approved" in result

    def test_execute_with_empty_pr_url_raises_error(self, use_case):
        """Test execution raises error when PR URL is empty."""
        # Arrange
        pr_url = ""
        compliment = "Nice PR!"

        # Act & Assert
        with pytest.raises(ValueError, match="PR URL cannot be empty"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

    def test_execute_with_none_pr_url_raises_error(self, use_case):
        """Test execution raises error when PR URL is None."""
        # Arrange
        pr_url = None
        compliment = "Nice PR!"

        # Act & Assert
        with pytest.raises(ValueError, match="PR URL cannot be empty"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

    def test_execute_with_empty_compliment_raises_error(self, use_case):
        """Test execution raises error when compliment is empty."""
        # Arrange
        pr_url = "https://github.com/owner/repo/pull/123"
        compliment = ""

        # Act & Assert
        with pytest.raises(ValueError, match="Compliment cannot be empty"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

    def test_execute_with_invalid_pr_url_type_raises_error(self, use_case):
        """Test execution raises error when PR URL is not a string."""
        # Arrange
        pr_url = 12345
        compliment = "Nice PR!"

        # Act & Assert
        with pytest.raises(ValueError, match="must be a string"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

    def test_execute_with_invalid_compliment_type_raises_error(self, use_case):
        """Test execution raises error when compliment is not a string."""
        # Arrange
        pr_url = "https://github.com/owner/repo/pull/123"
        compliment = 12345

        # Act & Assert
        with pytest.raises(ValueError, match="must be a string"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

    def test_execute_logs_on_start(self, use_case, mock_logger):
        """Test execution logs on start."""
        # Arrange
        pr_url = "https://github.com/owner/repo/pull/123"
        compliment = "Great work!"

        # Act
        import asyncio

        asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

        # Assert
        mock_logger.info.assert_called_once()

    def test_execute_returns_repository_result(self, use_case, mock_repository):
        """Test execution returns result from repository."""
        # Arrange
        pr_url = "https://github.com/owner/repo/pull/123"
        compliment = "Excellent PR!"
        expected_result = "Successfully approved PR #123 in owner/repo"
        mock_repository.approve_pr_with_comment.return_value = expected_result

        # Act
        import asyncio

        result = asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))

        # Assert
        assert result == expected_result

    def test_execute_propagates_repository_error(self, use_case, mock_repository):
        """Test execution propagates repository errors."""
        # Arrange
        pr_url = "https://github.com/owner/repo/pull/123"
        compliment = "Nice PR!"
        mock_repository.approve_pr_with_comment.side_effect = RuntimeError("API error")

        # Act & Assert
        with pytest.raises(RuntimeError, match="API error"):
            import asyncio

            asyncio.run(use_case.execute(pr_url=pr_url, compliment=compliment))
