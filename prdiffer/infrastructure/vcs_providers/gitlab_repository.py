"""GitLab VCS provider implementation.

This module implements VCSDiffRepositoryInterface for GitLab,
demonstrating multi-provider support capability.
"""

import logging
from typing import Optional
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.errors import (
    E5019_CONNECTION_ERROR,
    E5002_GITHUB_API_ERROR,
    E4002_PR_NOT_FOUND,
)

httpx = None

try:
    import httpx
except ImportError:
    pass

logger = logging.getLogger(__name__)


class GitLabVCSRepository(VCSDiffRepositoryInterface):
    """GitLab-specific implementation of VCS provider interface.

    This is a demonstration provider showing how to add
    new VCS providers to the system without modifying core code.

    NOTE: Full GitLab API integration not implemented in this demo.
    This provider returns mock data for structure demonstration.
    """

    def __init__(
        self,
        gitlab_token: Optional[str] = None,
    ):
        """Initialize GitLab VCS repository.

        Args:
            gitlab_token: GitLab personal access token
        """
        self._gitlab_token = gitlab_token
        self._headers = (
            {"PRIVATE-TOKEN": self._gitlab_token} if self._gitlab_token else {}
        )

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "gitlab"

    @property
    def provider_version(self) -> str:
        """Get provider API version."""
        return "v4"

    async def initialize(self) -> None:
        """Initialize GitLab connection.

        For demonstration, this validates that token is set
        if using API.

        Raises:
            RuntimeError: If initialization fails
        """
        if httpx:
            try:
                async with httpx.AsyncClient(
                    base_url="https://gitlab.com/api/v4", headers=self._headers
                ) as client:
                    response = await client.get("/user")
                    if response.status_code != 200:
                        raise PRDifferException(
                            f"Failed to initialize GitLab connection: {response.status_code}",
                            error_code=E5019_CONNECTION_ERROR,
                        )
            except Exception as e:
                raise PRDifferException(
                    f"GitLab connection error: {e}", error_code=E5019_CONNECTION_ERROR
                )

    async def get_pr_diff(self, owner: str, repo: str, pr: int) -> PRDiff:
        """Get merge request diff from GitLab.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            pr: Merge request number

        Returns:
            PRDiff: Complete merge request diff with file context

        Note:
            This demonstration returns mock data.
            Full implementation would use GitLab API:
            - https://docs.gitlab.com/ee/api/merge_requests.html
        """
        if httpx:
            try:
                path = f"{owner}%2F{repo}"
                async with httpx.AsyncClient(
                    base_url="https://gitlab.com/api/v4", headers=self._headers
                ) as client:
                    url = f"/projects/{path}/merge_requests/{pr}"
                    response = await client.get(url)

                    if response.status_code != 200:
                        raise PRDifferException(
                            f"Merge request not found: {response.status_code}",
                            error_code=E4002_PR_NOT_FOUND,
                        )

                    return PRDiff(files=[])
            except httpx.HTTPError as e:
                logger.error(
                    "GitLab API HTTP error when fetching MR diff",
                    extra={
                        "owner": owner,
                        "repo": repo,
                        "pr": pr,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise PRDifferException(
                    f"GitLab API error: {e}", error_code=E5002_GITHUB_API_ERROR
                ) from e
            except Exception as e:
                logger.error(
                    "Unexpected error when fetching GitLab MR diff",
                    extra={
                        "owner": owner,
                        "repo": repo,
                        "pr": pr,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise PRDifferException(
                    f"GitLab API error: {e}", error_code=E5002_GITHUB_API_ERROR
                ) from e
        else:
            return PRDiff(files=[])

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        """Get latest head commit SHA for merge request.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            pr: Merge request number

        Returns:
            str: Latest head commit SHA

        Note:
            This demonstration returns a mock SHA.
            Full implementation would use GitLab API.
        """
        if httpx:
            try:
                path = f"{owner}%2F{repo}"
                async with httpx.AsyncClient(
                    base_url="https://gitlab.com/api/v4", headers=self._headers
                ) as client:
                    url = f"/projects/{path}/merge_requests/{pr}"
                    response = await client.get(url)

                    if response.status_code != 200:
                        logger.warning(
                            "GitLab API returned non-200 status for commit SHA",
                            extra={
                                "owner": owner,
                                "repo": repo,
                                "pr": pr,
                                "status_code": response.status_code,
                            },
                        )
                        return "unknown"

                    mr_data = response.json()
                    return mr_data.get("sha", "unknown")
            except httpx.HTTPError as e:
                logger.error(
                    "GitLab API HTTP error when fetching commit SHA",
                    extra={
                        "owner": owner,
                        "repo": repo,
                        "pr": pr,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                return "unknown"
            except Exception as e:
                logger.error(
                    "Unexpected error when fetching GitLab commit SHA",
                    extra={
                        "owner": owner,
                        "repo": repo,
                        "pr": pr,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                return "unknown"
        else:
            return "mock-sha-1234567890"

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
