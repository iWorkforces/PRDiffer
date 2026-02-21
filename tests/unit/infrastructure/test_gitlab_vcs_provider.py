import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from prdiffer.infrastructure.vcs_providers.gitlab_repository import GitLabVCSRepository


def mock_gitlab_client():
    """Create a mock httpx client for GitLab tests."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sha": "mock-sha-123456789"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    return mock_client


class TestGitLabVCSRepository:
    """Tests for GitLab VCS provider implementation."""

    def test_provider_name_property(self):
        """Provider should return 'gitlab'."""
        provider = GitLabVCSRepository()
        assert provider.provider_name == "gitlab"

    def test_provider_version_property(self):
        """Provider should return 'v4'."""
        provider = GitLabVCSRepository()
        assert provider.provider_version == "v4"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Provider should initialize without errors."""
        provider = GitLabVCSRepository()
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_gitlab_client()
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_initialize_without_token(self):
        """Provider should initialize without token."""
        provider = GitLabVCSRepository()
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_gitlab_client()
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_get_pr_diff(self):
        """Provider should return diff files list."""
        provider = GitLabVCSRepository()
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_gitlab_client()
            await provider.initialize()
            diff = await provider.get_pr_diff("owner", "repo", 123)
            # PRDiff now uses frozen dataclass with tuple fields
            assert isinstance(diff.files, tuple)

    @pytest.mark.asyncio
    async def test_get_pr_diff_with_token(self):
        """Provider should return diff with token."""
        provider = GitLabVCSRepository("test-token")
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_gitlab_client()
            await provider.initialize()
            diff = await provider.get_pr_diff("owner", "repo", 123)
            assert isinstance(diff.files, tuple)

    @pytest.mark.asyncio
    async def test_get_latest_commit_sha(self):
        """Provider should return mock SHA."""
        provider = GitLabVCSRepository()
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_gitlab_client()
            await provider.initialize()
            sha = await provider.get_latest_commit_sha("owner", "repo", 123)
            assert sha == "mock-sha-123456789"

    @pytest.mark.asyncio
    async def test_get_latest_commit_sha_with_token(self):
        """Provider should return SHA with token."""
        provider = GitLabVCSRepository("test-token")
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_gitlab_client()
            await provider.initialize()
            sha = await provider.get_latest_commit_sha("owner", "repo", 123)
            assert sha == "mock-sha-123456789"

    def test_supports_repository_gitlab_url(self):
        """Provider should support GitLab URLs."""
        provider = GitLabVCSRepository()
        assert provider.supports_repository("https://gitlab.com/owner/repo/-/merge_requests/123")
        assert not provider.supports_repository("https://github.com/owner/repo/pull/123")

    def test_supports_repository_gitlab_tree_url(self):
        """Provider should support GitLab tree URLs."""
        provider = GitLabVCSRepository()
        assert provider.supports_repository("https://gitlab.com/owner/repo/-/tree/abcd1234")

    def test_does_not_support_github_url(self):
        """Provider should not support GitHub URLs."""
        provider = GitLabVCSRepository()
        assert not provider.supports_repository("https://github.com/owner/repo/pull/123")

    def test_supports_repository_invalid_url(self):
        """Provider should not support invalid URLs."""
        provider = GitLabVCSRepository()
        assert not provider.supports_repository("not-a-valid-url")

    @pytest.mark.asyncio
    async def test_get_latest_commit_sha_returns_unknown_without_httpx(self):
        """Provider should return 'unknown' when httpx not available."""
        provider = GitLabVCSRepository()
        sha = await provider.get_latest_commit_sha("owner", "repo", 123)
        assert sha == "unknown"
