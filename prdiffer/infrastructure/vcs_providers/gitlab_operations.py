"""Synchronous python-gitlab lifecycle and merge request operations."""

from urllib.parse import quote

import gitlab
import requests
from pydantic import BaseModel, ConfigDict, ValidationError

from prdiffer.domain.errors import E4002_PR_NOT_FOUND, E5002_GITHUB_API_ERROR, E5019_CONNECTION_ERROR
from prdiffer.domain.exceptions import PRDifferException


_NOT_FOUND_ERRORS = (
    gitlab.GitlabAuthenticationError,
    gitlab.GitlabGetError,
    gitlab.GitlabListError,
    gitlab.GitlabHttpError,
)
_READ_FAILURES = (
    gitlab.GitlabConnectionError,
    gitlab.GitlabParsingError,
    requests.RequestException,
    gitlab.GitlabError,
    ValidationError,
)


class GitLabDiffRecord(BaseModel):
    """Structured file diff response returned by GitLab's documented endpoint."""

    model_config = ConfigDict(frozen=True)

    old_path: str
    new_path: str
    new_file: bool
    deleted_file: bool
    renamed_file: bool
    diff: str | None = ""
    collapsed: bool = False
    too_large: bool = False


class GitLabOperations:
    """Execute isolated synchronous GitLab operations with fresh SDK clients."""

    def __init__(self, gitlab_token: str | None = None) -> None:
        """Store only the token used to construct operation-scoped SDK clients."""
        self._gitlab_token = gitlab_token

    def initialize(self) -> None:
        """Authenticate a newly created GitLab client."""
        try:
            with gitlab.Gitlab(url="https://gitlab.com", private_token=self._gitlab_token) as client:
                client.auth()
        except gitlab.GitlabError, requests.RequestException:
            raise PRDifferException("Failed to initialize GitLab connection", error_code=E5019_CONNECTION_ERROR) from None

    def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        """Read the nonempty current head SHA using GitLab's project managers."""
        try:
            with gitlab.Gitlab(url="https://gitlab.com", private_token=self._gitlab_token) as client:
                project = client.projects.get(f"{owner}/{repo}")
                merge_request = project.mergerequests.get(pr)
                sha = getattr(merge_request, "sha", None)
        except _NOT_FOUND_ERRORS:
            raise PRDifferException("Merge request not found", error_code=E4002_PR_NOT_FOUND) from None
        except _READ_FAILURES:
            raise PRDifferException("GitLab API error", error_code=E5002_GITHUB_API_ERROR) from None

        if not isinstance(sha, str) or not sha:
            raise PRDifferException("Merge request SHA is missing", error_code=E5002_GITHUB_API_ERROR)
        return sha

    def get_diff_records(self, owner: str, repo: str, pr: int) -> tuple[GitLabDiffRecord, ...]:
        """Read structured merge request diffs and compensate for absent paging headers."""
        path = f"/projects/{quote(f'{owner}/{repo}', safe='')}/merge_requests/{pr}/diffs"
        try:
            with gitlab.Gitlab(url="https://gitlab.com", private_token=self._gitlab_token) as client:
                records = [GitLabDiffRecord.model_validate(record) for record in client.http_list(path, get_all=True, per_page=100, unidiff=True)]
                if not records or len(records) % 100:
                    return tuple(records)

                page = len(records) // 100 + 1
                while True:
                    raw_next_records = client.http_list(path, page=page, get_all=False, per_page=100, unidiff=True)
                    next_records = [GitLabDiffRecord.model_validate(record) for record in raw_next_records]
                    records.extend(next_records)
                    if len(next_records) < 100:
                        return tuple(records)
                    page += 1
        except _NOT_FOUND_ERRORS:
            raise PRDifferException("Merge request not found", error_code=E4002_PR_NOT_FOUND) from None
        except _READ_FAILURES:
            raise PRDifferException("GitLab API error", error_code=E5002_GITHUB_API_ERROR) from None
