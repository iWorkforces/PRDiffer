"""GitLab VCS provider implementation."""

from typing import NotRequired, TypedDict
from urllib.parse import quote

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.errors import E4002_PR_NOT_FOUND, E5002_GITHUB_API_ERROR, E5019_CONNECTION_ERROR
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface

httpx = None

try:
    import httpx
except ImportError:
    pass


class GitLabDiffRecord(TypedDict):
    """GitLab merge request diff record."""

    old_path: str
    new_path: str
    new_file: bool
    deleted_file: bool
    renamed_file: bool
    diff: NotRequired[str]


class GitLabVCSRepository(VCSDiffRepositoryInterface):
    """GitLab-specific implementation of VCS provider interface."""

    def __init__(
        self,
        gitlab_token: str | None = None,
    ):
        """Initialize GitLab VCS repository.

        Args:
            gitlab_token: GitLab personal access token
        """
        self._gitlab_token = gitlab_token
        self._headers = {"PRIVATE-TOKEN": self._gitlab_token} if self._gitlab_token else {}

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "gitlab"

    @property
    def provider_version(self) -> str:
        """Get provider API version."""
        return "v4"

    async def initialize(self) -> None:
        """Validate the configured GitLab connection."""
        if httpx is None:
            raise PRDifferException("GitLab HTTP client is not available", error_code=E5019_CONNECTION_ERROR)

        try:
            async with httpx.AsyncClient(base_url="https://gitlab.com/api/v4", headers=self._headers) as client:
                response = await client.get("/user")
        except httpx.HTTPError as error:
            raise PRDifferException(f"GitLab connection error: {error}", error_code=E5019_CONNECTION_ERROR) from error

        if response.status_code != 200:
            raise PRDifferException(
                f"Failed to initialize GitLab connection: {response.status_code}",
                error_code=E5019_CONNECTION_ERROR,
            )

    async def get_pr_diff(self, owner: str, repo: str, pr: int) -> PRDiff:
        """Get and map every structured GitLab merge request diff page."""
        if httpx is None:
            raise PRDifferException("GitLab HTTP client is not available", error_code=E5019_CONNECTION_ERROR)

        url = f"/projects/{quote(f'{owner}/{repo}', safe='')}/merge_requests/{pr}/diffs"
        files: list[FileDiffResponse] = []
        page = 1
        try:
            async with httpx.AsyncClient(base_url="https://gitlab.com/api/v4", headers=self._headers) as client:
                while True:
                    response = await client.get(url, params={"page": page, "per_page": 100, "unidiff": True})
                    if response.status_code != 200:
                        raise PRDifferException(
                            f"Merge request not found: {response.status_code}",
                            error_code=E4002_PR_NOT_FOUND,
                        )
                    records: list[GitLabDiffRecord] = response.json()
                    files.extend(self._to_file_diff(record) for record in records)
                    next_page = response.headers.get("X-Next-Page", "")
                    if next_page:
                        page = int(next_page)
                    elif len(records) == 100:
                        page += 1
                    else:
                        break
        except httpx.HTTPError as error:
            raise PRDifferException(f"GitLab API error: {error}", error_code=E5002_GITHUB_API_ERROR) from error

        return PRDiff(files=tuple(files))

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        """Get the nonempty latest head commit SHA for a merge request."""
        if httpx is None:
            raise PRDifferException("GitLab HTTP client is not available", error_code=E5019_CONNECTION_ERROR)

        url = f"/projects/{quote(f'{owner}/{repo}', safe='')}/merge_requests/{pr}"
        try:
            async with httpx.AsyncClient(base_url="https://gitlab.com/api/v4", headers=self._headers) as client:
                response = await client.get(url)
        except httpx.HTTPError as error:
            raise PRDifferException(f"GitLab API error: {error}", error_code=E5002_GITHUB_API_ERROR) from error

        if response.status_code != 200:
            raise PRDifferException(
                f"Merge request not found: {response.status_code}",
                error_code=E4002_PR_NOT_FOUND,
            )
        merge_request: dict[str, str] = response.json()
        sha = merge_request.get("sha")
        if not sha:
            raise PRDifferException("Merge request SHA is missing", error_code=E5002_GITHUB_API_ERROR)
        return sha

    @staticmethod
    def _to_file_diff(record: GitLabDiffRecord) -> FileDiffResponse:
        """Map a GitLab diff record to the existing domain response."""
        patch = record.get("diff", "")
        match (record["new_file"], record["deleted_file"], record["renamed_file"]):
            case (True, False, False):
                path, status = record["new_path"], EDIT_TYPE.ADDED
            case (False, True, False):
                path, status = record["old_path"], EDIT_TYPE.DELETED
            case (False, False, True):
                path, status = record["new_path"], EDIT_TYPE.RENAMED
            case (False, False, False):
                path, status = record["new_path"], EDIT_TYPE.MODIFIED
            case _:
                raise PRDifferException("GitLab diff record has conflicting change flags", error_code=E5002_GITHUB_API_ERROR)

        return FileDiffResponse(
            path=path,
            status=status,
            stats=FileStats(
                additions=sum(line.startswith("+") and not line.startswith("+++") for line in patch.splitlines()),
                deletions=sum(line.startswith("-") and not line.startswith("---") for line in patch.splitlines()),
            ),
            diff=patch,
        )

    def supports_repository(self, url: str) -> bool:
        """Check if URL belongs to GitLab.

        Args:
            url: Repository URL

        Returns:
            bool: True if GitLab supports this URL
        """
        import re

        pattern = r"https://gitlab\.com/([^/]+)/([^/]+)(/-)?/(merge_requests|tree)/([a-zA-Z0-9]+)"
        return bool(re.match(pattern, url))
