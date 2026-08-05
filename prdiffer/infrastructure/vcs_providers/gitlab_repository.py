"""Async GitLab adapter that maps SDK responses into domain diff entities."""

import re

import anyio.to_thread

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.errors import E5002_GITHUB_API_ERROR
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface
from prdiffer.infrastructure.vcs_providers.gitlab_operations import GitLabDiffRecord, GitLabOperations


class GitLabVCSRepository(VCSDiffRepositoryInterface):
    """Provide the asynchronous VCS contract over synchronous GitLab SDK operations."""

    def __init__(self, gitlab_token: str | None = None) -> None:
        """Initialize the provider with its immutable SDK operations configuration."""
        self._operations = GitLabOperations(gitlab_token)

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "gitlab"

    @property
    def provider_version(self) -> str:
        """Get provider API version."""
        return "v4"

    async def initialize(self) -> None:
        """Validate the configured GitLab connection without blocking the event loop."""
        await anyio.to_thread.run_sync(self._operations.initialize, abandon_on_cancel=False)

    async def get_pr_diff(self, owner: str, repo: str, pr: int) -> PRDiff:
        """Get every GitLab merge request diff record and map it to the domain model."""
        records = await anyio.to_thread.run_sync(
            self._operations.get_diff_records,
            owner,
            repo,
            pr,
            abandon_on_cancel=False,
        )
        return PRDiff(files=tuple(self._to_file_diff(record) for record in records))

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        """Get the nonempty latest merge request head SHA without blocking the event loop."""
        return await anyio.to_thread.run_sync(
            self._operations.get_latest_commit_sha,
            owner,
            repo,
            pr,
            abandon_on_cancel=False,
        )

    @staticmethod
    def _to_file_diff(record: GitLabDiffRecord) -> FileDiffResponse:
        """Map a GitLab diff record to the existing domain response."""
        patch: str = record.diff if record.diff is not None else ""
        match (record.new_file, record.deleted_file, record.renamed_file):
            case (True, False, False):
                path, status = record.new_path, EDIT_TYPE.ADDED
            case (False, True, False):
                path, status = record.old_path, EDIT_TYPE.DELETED
            case (False, False, True):
                path, status = record.new_path, EDIT_TYPE.RENAMED
            case (False, False, False):
                path, status = record.new_path, EDIT_TYPE.MODIFIED
            case _:
                raise PRDifferException("GitLab diff record has conflicting change flags", error_code=E5002_GITHUB_API_ERROR)

        previous_path: str | None = None
        if status is EDIT_TYPE.RENAMED:
            # Mechanical mapping: use GitLab old_path when present and distinct.
            if record.old_path and record.old_path != path:
                previous_path = record.old_path

        return FileDiffResponse(
            path=path,
            status=status,
            stats=FileStats(
                additions=sum(line.startswith("+") and not line.startswith("+++") for line in patch.splitlines()),
                deletions=sum(line.startswith("-") and not line.startswith("---") for line in patch.splitlines()),
            ),
            diff=patch,
            previous_path=previous_path,
        )

    def supports_repository(self, url: str) -> bool:
        """Check whether the URL belongs to a supported canonical GitLab resource.

        Merge request URLs accept nested namespaces (group/subgroup/project).
        """
        if not isinstance(url, str) or not url:
            return False
        from prdiffer.infrastructure.utils.url_parser import parse_gitlab_merge_request_url
        from prdiffer.domain.exceptions import InvalidPRNumberError, InvalidURLError

        try:
            parse_gitlab_merge_request_url(url)
            return True
        except InvalidURLError, InvalidPRNumberError:
            pass

        # Legacy simple/nested tree URLs on GitLab.com (read-only support check).
        tree_pattern = re.compile(
            r"^https://gitlab\.com/(?:[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?/)+"
            r"-/tree/[a-zA-Z0-9._/-]+/?$"
        )
        return bool(tree_pattern.match(url.strip()))
