"""Unit tests for domain use cases.

Tests for the GetPRDiffUseCase which orchestrates PR diff retrieval
with caching and service coordination.
"""

from unittest.mock import Mock, AsyncMock
import pytest

from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.file_diff_response import (
    FileDiffResponse,
    FileStats,
    EDIT_TYPE,
)
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface


def create_sample_pr_diff() -> PRDiff:
    """Helper to create a sample PRDiff with the new structure."""
    return PRDiff(
        files=(
            FileDiffResponse(
                path="src/test.py",
                status=EDIT_TYPE.MODIFIED,
                stats=FileStats(additions=10, deletions=5),
                diff="test diff content",
            ),
        )
    )


@pytest.mark.unit
class TestGetPRDiffUseCase:
    """Unit tests for GetPRDiffUseCase."""

    @pytest.fixture
    def mock_pr_diff_service(self):
        """Mock PR diff service."""
        service = Mock(spec=PRDiffServiceInterface)
        service.get_pr_diff = AsyncMock()
        service.get_latest_commit_sha = AsyncMock(return_value="abc123def456")
        return service

    @pytest.fixture
    def mock_cache(self):
        """Mock cache service with async methods."""
        cache = Mock(spec=CacheServiceInterface)
        cache.get = AsyncMock(return_value=None)
        cache.get_cache_key = Mock(return_value="test-owner/test-repo/pr/123")
        cache.set = AsyncMock()
        cache.get_stats = Mock(return_value={"size": 0})
        return cache

    @pytest.fixture
    def use_case(self, mock_pr_diff_service, mock_cache):
        """Create use case with mocked dependencies."""
        return GetPRDiffUseCase(
            pr_diff_service=mock_pr_diff_service, cache_service=mock_cache
        )

    @pytest.mark.asyncio
    async def test_execute_with_cache_miss(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution when cache misses (fresh data required)."""
        # Arrange
        owner = "test-owner"
        repo = "test-repo"
        pr_number = 123
        current_commit = "abc123"
        fresh_pr_diff = create_sample_pr_diff()

        mock_cache.get.return_value = None  # Cache miss
        mock_pr_diff_service.get_pr_diff.return_value = fresh_pr_diff
        mock_pr_diff_service.get_latest_commit_sha.return_value = current_commit

        # Act
        result = await use_case.execute(owner, repo, pr_number)

        # Assert
        assert result == fresh_pr_diff
        mock_pr_diff_service.get_latest_commit_sha.assert_called_once_with(
            owner, repo, pr_number
        )
        mock_pr_diff_service.get_pr_diff.assert_called_once_with(owner, repo, pr_number)
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_cache_hit(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution when cache hits (data is fresh)."""
        # Arrange
        owner = "test-owner"
        repo = "test-repo"
        pr_number = 123
        cached_commit = "abc123"
        cached_pr_diff = create_sample_pr_diff()

        mock_cache.get.return_value = cached_pr_diff
        mock_pr_diff_service.get_latest_commit_sha.return_value = cached_commit

        # Act
        result = await use_case.execute(owner, repo, pr_number)

        # Assert
        assert result == cached_pr_diff
        mock_cache.get.assert_called_once()
        mock_pr_diff_service.get_pr_diff.assert_not_called()  # Should not call service
        mock_cache.set.assert_not_called()  # Should not update cache

    @pytest.mark.asyncio
    async def test_execute_with_stale_cache(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution when cache has stale data (commit SHA mismatch)."""
        # Arrange
        owner = "test-owner"
        repo = "test-repo"
        pr_number = 123
        current_commit = "new456"
        fresh_pr_diff = create_sample_pr_diff()

        # Cache returns None (commit SHA mismatch)
        mock_cache.get.return_value = None
        mock_pr_diff_service.get_latest_commit_sha.return_value = current_commit
        mock_pr_diff_service.get_pr_diff.return_value = fresh_pr_diff

        # Act
        result = await use_case.execute(owner, repo, pr_number)

        # Assert
        assert result == fresh_pr_diff
        mock_pr_diff_service.get_pr_diff.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_service_error(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution handles service errors gracefully."""
        # Arrange
        owner = "test-owner"
        repo = "test-repo"
        pr_number = 123

        mock_cache.get.return_value = None
        mock_pr_diff_service.get_latest_commit_sha.return_value = "abc123"
        mock_pr_diff_service.get_pr_diff.side_effect = Exception("Service error")

        # Act & Assert
        with pytest.raises(Exception, match="Service error"):
            await use_case.execute(owner, repo, pr_number)

        # Cache should not be set on error
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_custom_cache_key(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution with correct cache key format."""
        # Arrange
        owner = "my-owner"
        repo = "my-repo"
        pr_number = 456
        expected_cache_key = f"{owner}/{repo}/pr/{pr_number}"
        current_commit = "xyz789"
        fresh_pr_diff = create_sample_pr_diff()

        mock_cache.get_cache_key.return_value = expected_cache_key
        mock_cache.get.return_value = None
        mock_pr_diff_service.get_latest_commit_sha.return_value = current_commit
        mock_pr_diff_service.get_pr_diff.return_value = fresh_pr_diff

        # Act
        await use_case.execute(owner, repo, pr_number)

        # Assert - verify correct cache key format
        mock_cache.get_cache_key.assert_called_once_with(owner, repo, pr_number)
        mock_cache.get.assert_called_once_with(expected_cache_key, current_commit)

    @pytest.mark.asyncio
    async def test_execute_gets_latest_commit_sha(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test that latest commit SHA is retrieved for cache validation."""
        # Arrange
        owner = "owner"
        repo = "repo"
        pr_number = 789
        expected_commit = "latest123"

        mock_cache.get.return_value = None
        mock_pr_diff_service.get_latest_commit_sha.return_value = expected_commit
        mock_pr_diff_service.get_pr_diff.return_value = create_sample_pr_diff()

        # Act
        await use_case.execute(owner, repo, pr_number)

        # Assert
        mock_pr_diff_service.get_latest_commit_sha.assert_called_once_with(
            owner, repo, pr_number
        )

    @pytest.mark.asyncio
    async def test_execute_returns_none_on_no_commit(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution returns None when latest commit SHA cannot be retrieved."""
        # Arrange
        owner = "owner"
        repo = "repo"
        pr_number = 999

        mock_cache.get.return_value = None
        mock_pr_diff_service.get_latest_commit_sha.return_value = None  # No commit

        # Act
        result = await use_case.execute(owner, repo, pr_number)

        # Assert - should return None and not call get_pr_diff
        assert result is None
        mock_pr_diff_service.get_pr_diff.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_empty_cache_result(
        self, use_case, mock_pr_diff_service, mock_cache
    ):
        """Test execution when cache returns None (cache miss)."""
        # Arrange
        owner = "owner"
        repo = "repo"
        pr_number = 999
        current_commit = "commit999"

        # Cache returns None (cache miss)
        mock_cache.get.return_value = None
        mock_pr_diff_service.get_latest_commit_sha.return_value = current_commit
        mock_pr_diff_service.get_pr_diff.return_value = create_sample_pr_diff()

        # Act
        result = await use_case.execute(owner, repo, pr_number)

        # Assert - should fetch from service
        assert result is not None
        mock_pr_diff_service.get_pr_diff.assert_called_once()
        mock_cache.set.assert_called_once()
