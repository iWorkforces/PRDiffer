import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.exceptions import PRDifferException
import prdiffer.infrastructure.vcs_providers.gitlab_repository as gitlab_repository
from prdiffer.infrastructure.vcs_providers.gitlab_repository import GitLabVCSRepository


def mock_gitlab_client():
    """Create a mock httpx client for GitLab tests."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sha": "mock-sha-123456789"}
    mock_response.headers = {"X-Next-Page": ""}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    return mock_client


@dataclass(frozen=True)
class GitLabDiffResponse:
    payload: list[dict[str, str | bool]]
    next_page: str
    status_code: int = 200

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Next-Page": self.next_page}

    def json(self) -> list[dict[str, str | bool]]:
        return self.payload


class GitLabDiffClient:
    def __init__(self, responses: dict[int, GitLabDiffResponse]):
        self._responses = responses
        self.requested_pages: list[int] = []

    async def __aenter__(self) -> "GitLabDiffClient":
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    async def get(self, url: str, *, params: dict[str, int | bool]) -> GitLabDiffResponse:
        assert url == "/projects/owner%2Frepo/merge_requests/17/diffs"
        assert params["per_page"] == 100
        assert params["unidiff"] is True

        page = params["page"]
        assert isinstance(page, int)
        self.requested_pages.append(page)
        return self._responses[page]


class GitLabHTTPX:
    class HTTPError(Exception):
        pass

    def __init__(self, client: GitLabDiffClient):
        self._client = client

    def AsyncClient(self, *, base_url: str, headers: dict[str, str]) -> GitLabDiffClient:
        assert base_url == "https://gitlab.com/api/v4"
        assert headers == {}
        return self._client


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
            client = mock_gitlab_client()
            client.get.return_value.json.return_value = []
            mock_httpx.AsyncClient.return_value = client
            await provider.initialize()
            diff = await provider.get_pr_diff("owner", "repo", 123)
            assert diff == PRDiff(files=())

    @pytest.mark.asyncio
    async def test_get_pr_diff_with_token(self):
        """Provider should return diff with token."""
        provider = GitLabVCSRepository("test-token")
        with patch("prdiffer.infrastructure.vcs_providers.gitlab_repository.httpx") as mock_httpx:
            client = mock_gitlab_client()
            client.get.return_value.json.return_value = []
            mock_httpx.AsyncClient.return_value = client
            await provider.initialize()
            diff = await provider.get_pr_diff("owner", "repo", 123)
            assert diff == PRDiff(files=())

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
    async def test_get_latest_commit_sha_raises_without_httpx(self, monkeypatch: pytest.MonkeyPatch):
        """Provider should fail explicitly when its HTTP client is unavailable."""
        provider = GitLabVCSRepository()
        monkeypatch.setattr(gitlab_repository, "httpx", None)
        with pytest.raises(PRDifferException, match="HTTP client"):
            await provider.get_latest_commit_sha("owner", "repo", 123)

    @pytest.mark.anyio
    async def test_get_pr_diff_aggregates_pages_and_maps_gitlab_file_records(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        added_diff = "--- /dev/null\n+++ b/src/added.py\n+first\n+second"
        modified_diff = "--- a/src/current.py\n+++ b/src/current.py\n-old\n+new"
        renamed_diff = "--- a/src/old_name.py\n+++ b/src/new_name.py\n-old name\n+new name"
        deleted_diff = "--- a/src/removed.py\n+++ /dev/null\n-old"
        unchanged_flags = {
            "new_file": False,
            "renamed_file": False,
            "deleted_file": False,
            "collapsed": False,
            "too_large": False,
        }
        first_page = GitLabDiffResponse(
            payload=[
                {**unchanged_flags, "old_path": "src/added.py", "new_path": "src/added.py", "new_file": True, "diff": added_diff},
                {**unchanged_flags, "old_path": "src/current.py", "new_path": "src/current.py", "diff": modified_diff},
                {**unchanged_flags, "old_path": "src/old_name.py", "new_path": "src/new_name.py", "renamed_file": True, "diff": renamed_diff},
                {**unchanged_flags, "old_path": "src/removed.py", "new_path": "src/removed.py", "deleted_file": True, "diff": deleted_diff},
            ],
            next_page="2",
        )
        second_page = GitLabDiffResponse(
            payload=[
                {**unchanged_flags, "old_path": "src/collapsed.py", "new_path": "src/collapsed.py", "collapsed": True, "diff": ""},
                {**unchanged_flags, "old_path": "src/large.py", "new_path": "src/large.py", "too_large": True, "diff": ""},
            ],
            next_page="",
        )
        client = GitLabDiffClient({1: first_page, 2: second_page})
        monkeypatch.setattr(gitlab_repository, "httpx", GitLabHTTPX(client))

        # When
        diff = await GitLabVCSRepository().get_pr_diff("owner", "repo", 17)

        # Then
        assert client.requested_pages == [1, 2]
        assert diff == PRDiff(
            files=(
                FileDiffResponse("src/added.py", EDIT_TYPE.ADDED, FileStats(additions=2, deletions=0), added_diff),
                FileDiffResponse("src/current.py", EDIT_TYPE.MODIFIED, FileStats(additions=1, deletions=1), modified_diff),
                FileDiffResponse("src/new_name.py", EDIT_TYPE.RENAMED, FileStats(additions=1, deletions=1), renamed_diff),
                FileDiffResponse("src/removed.py", EDIT_TYPE.DELETED, FileStats(additions=0, deletions=1), deleted_diff),
                FileDiffResponse("src/collapsed.py", EDIT_TYPE.MODIFIED, FileStats(), ""),
                FileDiffResponse("src/large.py", EDIT_TYPE.MODIFIED, FileStats(), ""),
            )
        )

    @pytest.mark.anyio
    async def test_get_pr_diff_requests_another_page_when_gitlab_omits_pagination_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        record = {
            "old_path": "src/file.py",
            "new_path": "src/file.py",
            "new_file": False,
            "renamed_file": False,
            "deleted_file": False,
            "diff": "+line",
        }
        client = GitLabDiffClient(
            {
                1: GitLabDiffResponse(payload=[record] * 100, next_page=""),
                2: GitLabDiffResponse(payload=[], next_page=""),
            }
        )
        monkeypatch.setattr(gitlab_repository, "httpx", GitLabHTTPX(client))

        # When
        diff = await GitLabVCSRepository().get_pr_diff("owner", "repo", 17)

        # Then
        assert client.requested_pages == [1, 2]
        assert len(diff.files) == 100
