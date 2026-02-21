"""Unit tests for PR diff use case.

Tests for GetPRDiffUseCase which orchestrates PR diff retrieval
with commit-based caching.
"""

import asyncio
from unittest.mock import Mock, AsyncMock

import pytest

from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase


@pytest.mark.unit
class TestGetPRDiffUseCase:
    """Unit tests for GetPRDiffUseCase."""

    @pytest.fixture
    def mock_pr_diff_service(self):
        """Mock PR diff service."""
        service = Mock(spec=PRDiffServiceInterface)
        service.get_latest_commit_sha = AsyncMock()
        service.get_pr_diff = AsyncMock()
        return service

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        service = Mock(spec=CacheServiceInterface)
        service.get_cache_key = Mock(return_value='owner/repo/pr/123')
        service.get = AsyncMock(return_value=None)
        service.set = AsyncMock()
        return service

    @pytest.fixture
    def use_case(self, mock_pr_diff_service, mock_cache_service):
        """Create use case with mocked dependencies."""
        return GetPRDiffUseCase(
            pr_diff_service=mock_pr_diff_service,
            cache_service=mock_cache_service,
        )

    @pytest.fixture
    def sample_pr_diff(self):
        """Create a sample PRDiff for testing."""
        return PRDiff(files=())

    def test_cache_hit_returns_cached_result(self, use_case, mock_pr_diff_service, mock_cache_service, sample_pr_diff):
        """Test that cached result is returned when cache hit occurs."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'abc123'
        mock_cache_service.get.return_value = sample_pr_diff

        # Act
        result = asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

        # Assert
        assert result is sample_pr_diff
        mock_cache_service.get_cache_key.assert_called_once_with('owner', 'repo', 123)
        mock_pr_diff_service.get_latest_commit_sha.assert_called_once_with('owner', 'repo', 123)
        mock_cache_service.get.assert_called_once_with('owner/repo/pr/123', 'abc123')
        # Should NOT call get_pr_diff when cache hit
        mock_pr_diff_service.get_pr_diff.assert_not_called()
        # Should NOT call cache set when cache hit
        mock_cache_service.set.assert_not_called()

    def test_cache_miss_fetches_and_caches(self, use_case, mock_pr_diff_service, mock_cache_service, sample_pr_diff):
        """Test that diff is fetched and cached when cache miss occurs."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'abc123'
        mock_cache_service.get.return_value = None
        mock_pr_diff_service.get_pr_diff.return_value = sample_pr_diff

        # Act
        result = asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

        # Assert
        assert result is sample_pr_diff
        mock_pr_diff_service.get_pr_diff.assert_called_once_with('owner', 'repo', 123)
        mock_cache_service.set.assert_called_once_with('owner/repo/pr/123', 'abc123', sample_pr_diff)

    def test_returns_none_when_commit_sha_not_found(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that None is returned when commit SHA cannot be retrieved."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = None

        # Act
        result = asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

        # Assert
        assert result is None
        mock_cache_service.get_cache_key.assert_called_once_with('owner', 'repo', 123)
        mock_pr_diff_service.get_latest_commit_sha.assert_called_once_with('owner', 'repo', 123)
        # Should NOT attempt cache lookup or diff fetch
        mock_cache_service.get.assert_not_called()
        mock_pr_diff_service.get_pr_diff.assert_not_called()

    def test_returns_none_when_diff_fetch_fails(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that None is returned when diff fetch returns None."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'abc123'
        mock_cache_service.get.return_value = None
        mock_pr_diff_service.get_pr_diff.return_value = None

        # Act
        result = asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

        # Assert
        assert result is None
        mock_pr_diff_service.get_pr_diff.assert_called_once_with('owner', 'repo', 123)
        # Should NOT cache None result
        mock_cache_service.set.assert_not_called()

    def test_does_not_cache_none_result(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that None results are not stored in cache."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'def456'
        mock_cache_service.get.return_value = None
        mock_pr_diff_service.get_pr_diff.return_value = None

        # Act
        asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=99))

        # Assert
        mock_cache_service.set.assert_not_called()

    def test_propagates_service_exception(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that exceptions from the PR diff service propagate."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'abc123'
        mock_cache_service.get.return_value = None
        mock_pr_diff_service.get_pr_diff.side_effect = RuntimeError('API error')

        # Act & Assert
        with pytest.raises(RuntimeError, match='API error'):
            asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

    def test_propagates_commit_sha_exception(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that exceptions from get_latest_commit_sha propagate."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.side_effect = RuntimeError('Connection failed')

        # Act & Assert
        with pytest.raises(RuntimeError, match='Connection failed'):
            asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

    def test_propagates_cache_get_exception(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that exceptions from cache get propagate."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'abc123'
        mock_cache_service.get.side_effect = RuntimeError('Cache error')

        # Act & Assert
        with pytest.raises(RuntimeError, match='Cache error'):
            asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

    def test_cache_key_generation(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that cache key is generated with correct parameters."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'abc123'
        mock_cache_service.get.return_value = None
        mock_pr_diff_service.get_pr_diff.return_value = None

        # Act
        asyncio.run(use_case.execute(repo_owner='my-org', repo_name='my-repo', pr_number=42))

        # Assert
        mock_cache_service.get_cache_key.assert_called_once_with('my-org', 'my-repo', 42)

    def test_commit_sha_passed_to_cache_get(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that current commit SHA is used for cache validation."""
        # Arrange
        mock_pr_diff_service.get_latest_commit_sha.return_value = 'sha_xyz789'
        mock_cache_service.get.return_value = None
        mock_pr_diff_service.get_pr_diff.return_value = None

        # Act
        asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=1))

        # Assert
        mock_cache_service.get.assert_called_once_with('owner/repo/pr/123', 'sha_xyz789')

    def test_empty_string_commit_sha_returns_none(self, use_case, mock_pr_diff_service, mock_cache_service):
        """Test that empty string commit SHA causes early return of None."""
        # Arrange - empty string is falsy
        mock_pr_diff_service.get_latest_commit_sha.return_value = ''

        # Act
        result = asyncio.run(use_case.execute(repo_owner='owner', repo_name='repo', pr_number=123))

        # Assert
        assert result is None
        mock_cache_service.get.assert_not_called()
        mock_pr_diff_service.get_pr_diff.assert_not_called()

    def test_constructor_stores_dependencies(self):
        """Test that constructor properly stores injected dependencies."""
        # Arrange
        mock_pr_diff_service = Mock(spec=PRDiffServiceInterface)
        mock_cache_service = Mock(spec=CacheServiceInterface)

        # Act
        use_case = GetPRDiffUseCase(
            pr_diff_service=mock_pr_diff_service,
            cache_service=mock_cache_service,
        )

        # Assert
        assert use_case._pr_diff_service is mock_pr_diff_service
        assert use_case._cache_service is mock_cache_service
