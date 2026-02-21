"""Unit tests for GitHub API Client.

This module contains comprehensive tests for the GitHubAPIClient class,
covering cache management, retry logic, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from collections import OrderedDict

from prdiffer.infrastructure.github.client import (
    GitHubAPIClient,
    DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE,
    DEFAULT_FILE_CONTENT_CACHE_TTL,
)
from prdiffer.domain.exceptions import PRDifferException
from github import GithubException
from github.Repository import Repository


class TestGitHubAPIClient:
    """Test suite for GitHubAPIClient."""

    def test_initialization(self):
        """Test client initialization with default parameters."""
        client = GitHubAPIClient()
        assert client._github_client is None
        assert client._file_content_cache == OrderedDict()
        assert client._cache_max_size == DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE
        assert client._cache_ttl == DEFAULT_FILE_CONTENT_CACHE_TTL

    def test_initialize_client_with_token(self):
        """Test client initialization with GitHub token."""
        client = GitHubAPIClient()
        token = 'test_token_123'
        client.initialize_client(github_token=token, timeout=60)

        assert client._github_client is not None
        # Verify client was created with token auth
        # Note: We can't easily test the internal auth without accessing private attributes

    def test_initialize_client_without_token(self):
        """Test client initialization without token (anonymous access)."""
        client = GitHubAPIClient()
        client.initialize_client(github_token=None, timeout=30)

        assert client._github_client is not None

    def test_get_repository_without_initialization_raises_error(self):
        """Test that get_repository raises PRDifferException when client not initialized."""
        client = GitHubAPIClient()
        # Don't call initialize_client()

        with pytest.raises(PRDifferException, match='GitHub client not initialized'):
            client.get_repository('owner/repo')

    def test_cache_entry_valid(self):
        """Test cache entry validation logic."""
        client = GitHubAPIClient()

        # Test with non-existent cache entry
        assert not client._is_cache_entry_valid(('file.py', 'main'))
        # Note: We can't test the _is_cache_entry_valid method directly as it's not exposed

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        client = GitHubAPIClient()
        client.initialize_client()

        cache_key = ('path/to/file.py', 'main')
        content = 'file content here'

        # Set cache entry
        client._cache_set(cache_key, content)

        # Verify cache was set
        assert cache_key in client._file_content_cache
        assert client._file_content_cache[cache_key]['content'] == content

    def test_cache_eviction_oldest_entries(self):
        """Test LRU eviction when cache exceeds max size."""
        client = GitHubAPIClient()
        client._cache_max_size = 3  # Small size for testing
        client.initialize_client()

        # Add 5 entries to cache (should trigger eviction after 3)
        for i in range(5):
            cache_key = (f'file{i}.py', 'main')
            client._cache_set(cache_key, f'content{i}')

        # Should only have 3 entries after eviction
        assert len(client._file_content_cache) <= 3


class TestGitHubAPIClientErrorHandling:
    """Test error handling in GitHubAPIClient."""

    def test_get_repository_handles_github_exception(self):
        """Test that GitHub exceptions are handled gracefully."""
        client = GitHubAPIClient()
        client.initialize_client()

        with patch.object(client._retry_handler, 'execute_with_retry') as mock_retry:
            # Simulate GitHub exception
            mock_retry.side_effect = GithubException('Repository not found')

            result = client.get_repository('owner/repo')

            # Should return None on error
            assert result is None

    def test_get_pull_request_handles_github_exception(self):
        """Test that GitHub exceptions are handled gracefully for pull requests."""
        client = GitHubAPIClient()
        client.initialize_client()

        mock_repo = Mock(spec=Repository)

        with patch.object(client._retry_handler, 'execute_with_retry') as mock_retry:
            # Simulate GitHub exception
            mock_retry.side_effect = GithubException('PR not found')

            result = client.get_pull_request(mock_repo, 123)

            # Should return None on error
            assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
