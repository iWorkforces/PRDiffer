"""Comprehensive tests for GitHubAPIClient."""

import time
import pytest
from unittest.mock import MagicMock, patch
from collections import OrderedDict
from github import GithubException

from prdiffer.infrastructure.github.client import (
    GitHubAPIClient,
    get_github_api_client,
    DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE,
    DEFAULT_FILE_CONTENT_CACHE_TTL,
    GITHUB_API_EXCEPTIONS,
)
from prdiffer.domain.exceptions import PRDifferException


@pytest.fixture
def api_client():
    """Create API client for testing."""
    client = GitHubAPIClient()
    client.initialize_client()
    return client


@pytest.fixture
def api_client_no_init():
    """Create API client without initialization."""
    return GitHubAPIClient()


class TestGitHubAPIClientInit:
    """Tests for GitHubAPIClient initialization."""

    def test_init_defaults(self):
        """Test initialization with default parameters."""
        client = GitHubAPIClient()

        assert client._github_client is None
        assert client._file_content_cache == OrderedDict()
        assert client._cache_max_size == DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE
        assert client._cache_ttl == DEFAULT_FILE_CONTENT_CACHE_TTL
        assert client._cache_hits == 0
        assert client._cache_misses == 0
        assert client._cache_evictions == 0

    def test_init_custom_cache_settings(self):
        """Test initialization with custom cache settings."""
        client = GitHubAPIClient(
            file_content_cache_max_size=500,
            file_content_cache_ttl=300,
        )

        assert client._cache_max_size == 500
        assert client._cache_ttl == 300

    def test_init_with_custom_logger(self):
        """Test initialization with custom logger."""
        mock_logger = MagicMock()
        client = GitHubAPIClient(logger=mock_logger)

        assert client._logger is mock_logger

    def test_init_simple_retry_handler(self):
        """Test initialization with simple retry handler."""
        client = GitHubAPIClient(use_advanced_retry=False)

        assert client._retry_handler is not None

    def test_init_advanced_retry_handler(self):
        """Test initialization with advanced retry handler."""
        client = GitHubAPIClient(use_advanced_retry=True)

        assert client._retry_handler is not None


class TestInitializeClient:
    """Tests for initialize_client method."""

    def test_initialize_with_token(self):
        """Test client initialization with token."""
        client = GitHubAPIClient()
        client.initialize_client(github_token='test_token', timeout=60)

        assert client._github_client is not None

    def test_initialize_without_token(self):
        """Test client initialization without token."""
        client = GitHubAPIClient()
        client.initialize_client(github_token=None, timeout=30)

        assert client._github_client is not None

    def test_reinitialize(self):
        """Test reinitializing the client."""
        client = GitHubAPIClient()
        client.initialize_client(github_token='token1', timeout=30)
        first_client = client._github_client

        client.initialize_client(github_token='token2', timeout=60)

        assert client._github_client is not first_client


class TestGetRepository:
    """Tests for get_repository method."""

    def test_get_repository_without_init_raises(self, api_client_no_init):
        """Test that get_repository raises without initialization."""
        with pytest.raises(PRDifferException, match='GitHub client not initialized'):
            api_client_no_init.get_repository('owner/repo')

    def test_get_repository_success(self, api_client):
        """Test successful repository retrieval."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_repo = MagicMock()
            mock_repo.full_name = 'owner/repo'
            mock_repo.name = 'repo'
            mock_repo.owner.login = 'owner'
            mock_repo.html_url = 'https://github.com/owner/repo'
            mock_retry.return_value = mock_repo

            result = api_client.get_repository('owner/repo')

            assert result is not None
            mock_retry.assert_called_once()

    def test_get_repository_not_found(self, api_client):
        """Test repository not found."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.side_effect = GithubException(404, 'Not Found', {})

            result = api_client.get_repository('owner/nonexistent')

            assert result is None

    def test_get_repository_github_exception(self, api_client):
        """Test handling of GitHub exception."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.side_effect = GithubException(500, 'Server Error', {})

            result = api_client.get_repository('owner/repo')

            assert result is None


class TestGetPullRequest:
    """Tests for get_pull_request method."""

    def test_get_pull_request_without_init_raises(self, api_client_no_init):
        """Test that get_pull_request raises without initialization."""
        with pytest.raises(PRDifferException, match='GitHub client not initialized'):
            api_client_no_init.get_pull_request('owner/repo', 123)

    def test_get_pull_request_success(self, api_client):
        """Test successful PR retrieval."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_repo = MagicMock()
            mock_pr = MagicMock()
            mock_pr.number = 123
            mock_pr.title = 'Test PR'
            mock_pr.state = 'open'
            mock_retry.side_effect = [mock_repo, mock_pr]

            result = api_client.get_pull_request('owner/repo', 123)

            assert result is not None

    def test_get_pull_request_not_found(self, api_client):
        """Test PR not found."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.side_effect = GithubException(404, 'Not Found', {})

            result = api_client.get_pull_request('owner/repo', 999)

            assert result is None

    def test_get_pull_request_repo_not_found(self, api_client):
        """Test when repository not found."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.return_value = None

            result = api_client.get_pull_request('owner/nonexistent', 123)

            assert result is None


class TestGetPyGithubRepository:
    """Tests for _get_pygithub_repository method."""

    def test_internal_get_repository_without_init_raises(self, api_client_no_init):
        """Test that internal method raises without initialization."""
        with pytest.raises(PRDifferException, match='GitHub client not initialized'):
            api_client_no_init._get_pygithub_repository('owner/repo')

    def test_internal_get_repository_success(self, api_client):
        """Test internal repository retrieval."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_repo = MagicMock()
            mock_retry.return_value = mock_repo

            result = api_client._get_pygithub_repository('owner/repo')

            assert result is mock_repo

    def test_internal_get_repository_error(self, api_client):
        """Test internal repository retrieval error."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.side_effect = GithubException(403, 'Forbidden', {})

            result = api_client._get_pygithub_repository('owner/repo')

            assert result is None


class TestGetPyGithubPullRequest:
    """Tests for _get_pygithub_pull_request method."""

    def test_internal_get_pr_success(self, api_client):
        """Test internal PR retrieval."""
        mock_repo = MagicMock()
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_pr = MagicMock()
            mock_retry.return_value = mock_pr

            result = api_client._get_pygithub_pull_request(mock_repo, 123)

            assert result is mock_pr

    def test_internal_get_pr_error(self, api_client):
        """Test internal PR retrieval error."""
        mock_repo = MagicMock()
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.side_effect = GithubException(404, 'Not Found', {})

            result = api_client._get_pygithub_pull_request(mock_repo, 999)

            assert result is None


class TestFileContentCaching:
    """Tests for file content caching methods."""

    def test_cache_set_and_get(self, api_client):
        """Test basic cache set and get."""
        cache_key = ('path/to/file.py', 'main')
        content = 'file content'

        api_client._cache_set(cache_key, content)

        assert cache_key in api_client._file_content_cache
        assert api_client._file_content_cache[cache_key]['content'] == content

    def test_cache_get_valid_entry(self, api_client):
        """Test getting a valid cached entry."""
        cache_key = ('file.py', 'main')
        content = 'content'
        api_client._cache_set(cache_key, content)

        result = api_client._cache_get(cache_key)

        assert result == content
        assert api_client._cache_hits == 1

    def test_cache_get_expired_entry(self, api_client):
        """Test getting an expired cached entry."""
        cache_key = ('file.py', 'main')
        api_client._file_content_cache[cache_key] = {
            'content': 'old content',
            'timestamp': time.time() - api_client._cache_ttl - 100,
        }

        result = api_client._cache_get(cache_key)

        assert result is None
        assert api_client._cache_misses == 1
        assert cache_key not in api_client._file_content_cache

    def test_cache_get_nonexistent_entry(self, api_client):
        """Test getting a nonexistent cached entry."""
        result = api_client._cache_get(('nonexistent.py', 'main'))

        assert result is None
        assert api_client._cache_misses == 1

    def test_cache_entry_valid_check(self, api_client):
        """Test cache entry validity check."""
        cache_key = ('file.py', 'main')

        assert not api_client._is_cache_entry_valid(cache_key)

        api_client._cache_set(cache_key, 'content')

        assert api_client._is_cache_entry_valid(cache_key)

    def test_cache_entry_expired_check(self, api_client):
        """Test cache entry expiration check."""
        cache_key = ('file.py', 'main')
        api_client._file_content_cache[cache_key] = {
            'content': 'content',
            'timestamp': time.time() - api_client._cache_ttl - 100,
        }

        assert not api_client._is_cache_entry_valid(cache_key)

    def test_lru_eviction(self, api_client):
        """Test LRU eviction when cache is full."""
        api_client._cache_max_size = 3

        for i in range(5):
            api_client._cache_set((f'file{i}.py', 'main'), f'content{i}')

        assert len(api_client._file_content_cache) <= 3
        assert api_client._cache_evictions > 0

    def test_lru_access_order(self, api_client):
        """Test that cache access updates LRU order."""
        api_client._cache_max_size = 3

        api_client._cache_set(('file1.py', 'main'), 'content1')
        api_client._cache_set(('file2.py', 'main'), 'content2')
        api_client._cache_set(('file3.py', 'main'), 'content3')

        api_client._cache_get(('file1.py', 'main'))

        keys = list(api_client._file_content_cache.keys())
        assert keys[-1] == ('file1.py', 'main')

    def test_cache_update_moves_to_end(self, api_client):
        """Test that cache update moves entry to end."""
        api_client._cache_set(('file1.py', 'main'), 'content1')
        api_client._cache_set(('file2.py', 'main'), 'content2')

        api_client._cache_set(('file1.py', 'main'), 'updated content')

        keys = list(api_client._file_content_cache.keys())
        assert keys[-1] == ('file1.py', 'main')


class TestGetFileContent:
    """Tests for get_file_content method."""

    def test_get_file_content_without_init_raises(self, api_client_no_init):
        """Test that get_file_content raises without initialization."""
        with pytest.raises(PRDifferException, match='GitHub client not initialized'):
            api_client_no_init.get_file_content('owner/repo', 'file.py', 'main')

    def test_get_file_content_from_cache(self, api_client):
        """Test getting file content from cache."""
        cache_key = ('file.py', 'main')
        api_client._cache_set(cache_key, 'cached content')

        result = api_client.get_file_content('owner/repo', 'file.py', 'main')

        assert result == 'cached content'

    def test_get_file_content_from_api(self, api_client):
        """Test getting file content from API."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_repo = MagicMock()
            mock_content = MagicMock()
            mock_content.decoded_content = b'file content from api'
            mock_retry.side_effect = [mock_repo, mock_content]

            result = api_client.get_file_content('owner/repo', 'file.py', 'main')

            assert result == 'file content from api'

    def test_get_file_content_directory(self, api_client):
        """Test getting directory instead of file."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_repo = MagicMock()
            mock_retry.side_effect = [mock_repo, [MagicMock(), MagicMock()]]

            result = api_client.get_file_content('owner/repo', 'dir/', 'main')

            assert result == ''

    def test_get_file_content_error(self, api_client):
        """Test handling error when getting file content."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.side_effect = GithubException(404, 'Not Found', {})

            result = api_client.get_file_content('owner/repo', 'file.py', 'main')

            assert result == ''

    def test_get_file_content_repo_not_found(self, api_client):
        """Test when repository not found."""
        with patch.object(api_client._retry_handler, 'execute_with_retry') as mock_retry:
            mock_retry.return_value = None

            result = api_client.get_file_content('owner/repo', 'file.py', 'main')

            assert result == ''


class TestGetFilesContentBatch:
    """Tests for get_files_content_batch method."""

    def test_batch_all_cached(self, api_client):
        """Test batch retrieval when all files are cached."""
        api_client._cache_set(('file1.py', 'main'), 'content1')
        api_client._cache_set(('file2.py', 'main'), 'content2')

        with patch.object(api_client, 'get_file_content') as mock_get:
            result = api_client.get_files_content_batch('owner/repo', ['file1.py', 'file2.py'], 'main')

            assert result['file1.py'] == 'content1'
            assert result['file2.py'] == 'content2'
            mock_get.assert_not_called()

    def test_batch_partial_cache(self, api_client):
        """Test batch retrieval with partial cache."""
        api_client._cache_set(('file1.py', 'main'), 'cached content')

        with patch.object(api_client, 'get_file_content', return_value='api content') as mock_get:
            result = api_client.get_files_content_batch('owner/repo', ['file1.py', 'file2.py'], 'main')

            assert result['file1.py'] == 'cached content'
            assert result['file2.py'] == 'api content'
            mock_get.assert_called_once_with('owner/repo', 'file2.py', 'main')

    def test_batch_empty_list(self, api_client):
        """Test batch retrieval with empty file list."""
        result = api_client.get_files_content_batch('owner/repo', [], 'main')

        assert result == {}


class TestExtractFileContent:
    """Tests for _extract_file_content method."""

    def test_extract_content_success(self, api_client):
        """Test successful content extraction."""
        mock_content = MagicMock()
        mock_content.decoded_content = b'file content'

        result = api_client._extract_file_content(mock_content)

        assert result == 'file content'

    def test_extract_content_no_decoded_content(self, api_client):
        """Test extraction with no decoded content."""
        mock_content = MagicMock()
        mock_content.decoded_content = None

        result = api_client._extract_file_content(mock_content)

        assert result == ''

    def test_extract_content_none(self, api_client):
        """Test extraction with None content."""
        result = api_client._extract_file_content(None)

        assert result == ''


class TestETagMethods:
    """Tests for ETag-related methods."""

    def test_get_etag_stats(self, api_client):
        """Test getting ETag stats."""
        result = api_client.get_etag_stats()

        assert isinstance(result, dict)

    def test_clear_etag_cache(self, api_client):
        """Test clearing ETag cache."""
        api_client.clear_etag_cache()
        result = api_client.get_etag_stats()

        assert result.get('cache_size', 0) == 0


class TestEvictOldestEntries:
    """Tests for _evict_oldest_entries method."""

    def test_evict_expired_entries(self, api_client):
        """Test eviction of expired entries."""
        api_client._file_content_cache[('old.py', 'main')] = {
            'content': 'old',
            'timestamp': time.time() - api_client._cache_ttl - 100,
        }
        api_client._file_content_cache[('new.py', 'main')] = {
            'content': 'new',
            'timestamp': time.time(),
        }

        api_client._evict_oldest_entries()

        assert ('old.py', 'main') not in api_client._file_content_cache
        assert ('new.py', 'main') in api_client._file_content_cache

    def test_evict_on_size_limit(self, api_client):
        """Test eviction when size limit is reached."""
        api_client._cache_max_size = 2

        api_client._cache_set(('file1.py', 'main'), 'content1')
        api_client._cache_set(('file2.py', 'main'), 'content2')
        api_client._cache_set(('file3.py', 'main'), 'content3')

        assert len(api_client._file_content_cache) <= 2


class TestGetGitHubApiClient:
    """Tests for get_github_api_client factory function."""

    def test_factory_defaults(self):
        """Test factory with default parameters."""
        client = get_github_api_client()

        assert client is not None
        assert isinstance(client, GitHubAPIClient)

    def test_factory_custom_params(self):
        """Test factory with custom parameters."""
        client = get_github_api_client(
            max_retries=5,
            retry_delay=2.0,
            timeout=60,
            circuit_breaker_enabled=False,
        )

        assert client is not None

    def test_factory_with_none_rate_limit_params(self):
        """Test factory with None rate limit parameters (uses settings)."""
        client = get_github_api_client(
            rate_limit_remaining_threshold=None,
            rate_limit_reset_buffer=None,
            secondary_rate_limit_backoff=None,
        )

        assert client is not None

    def test_factory_simple_retry(self):
        """Test factory with simple retry handler."""
        client = get_github_api_client(use_advanced_retry=False)

        assert client is not None


@pytest.mark.anyio
class TestAsyncFileContentMethods:
    """Tests for async file content methods."""

    async def test_get_file_content_async_from_cache(self, api_client):
        """Test async getting file content from cache."""
        cache_key = ('file.py', 'main')
        api_client._cache_set(cache_key, 'cached content')

        result = await api_client._get_file_content_async('owner/repo', 'file.py', 'main')

        assert result == 'cached content'

    async def test_get_file_content_async_without_init_raises(self, api_client_no_init):
        """Test that async method raises without initialization."""
        with pytest.raises(PRDifferException, match='GitHub client not initialized'):
            await api_client_no_init._get_file_content_async('owner/repo', 'file.py', 'main')

    async def test_get_files_content_batch_parallel_async(self, api_client):
        """Test async batch file content retrieval."""
        api_client._cache_set(('file1.py', 'main'), 'content1')
        api_client._cache_set(('file2.py', 'main'), 'content2')

        result = await api_client._get_files_content_batch_parallel_async('owner/repo', ['file1.py', 'file2.py'], 'main')

        assert result['file1.py'] == 'content1'
        assert result['file2.py'] == 'content2'

    async def test_get_files_content_batch_parallel_empty(self, api_client):
        """Test async batch with empty file list."""
        result = await api_client._get_files_content_batch_parallel_async('owner/repo', [], 'main')

        assert result == {}


class TestGithubApiExceptions:
    """Tests for exception handling."""

    def test_github_api_exceptions_tuple(self):
        """Test that GITHUB_API_EXCEPTIONS contains expected exceptions."""
        assert GithubException in GITHUB_API_EXCEPTIONS
        assert TimeoutError in GITHUB_API_EXCEPTIONS
        assert ConnectionError in GITHUB_API_EXCEPTIONS
        assert OSError in GITHUB_API_EXCEPTIONS
        assert RuntimeError in GITHUB_API_EXCEPTIONS
        assert ValueError in GITHUB_API_EXCEPTIONS
        assert TypeError in GITHUB_API_EXCEPTIONS
