"""GitLab VCS provider implementation.

This module implements VCSDiffRepositoryInterface for GitLab,
demonstrating multi-provider support capability.
"""

from typing import Optional
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface
from prdiffer.domain.entities.pr_diff import PRDiff

httpx = None

try:
    import httpx
except ImportError:
    pass


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
                        raise RuntimeError(
                            f"Failed to initialize GitLab connection: {response.status_code}"
                        )
            except Exception as e:
                raise RuntimeError(f"GitLab connection error: {e}")

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
                        raise RuntimeError(
                            f"Merge request not found: {response.status_code}"
                        )

                    mr_data = response.json()
                    diff_content = '{{"Mock GitLab MR diff for MR #{}"}}\n'.format(pr)
                    diff_content += "This is a demonstration provider.\n"
                    diff_content += "In production, this would contain the actual diff from GitLab API.\n"
                    base_sha = mr_data.get("diff_refs", {}).get("base_sha", "unknown")
                    diff_content += "Base SHA: {}\n".format(base_sha)
                    head_sha = mr_data.get("diff_refs", {}).get("head_sha", "unknown")
                    diff_content += "Head SHA: {}\n".format(head_sha)

                    return PRDiff(diff_content=diff_content)
            except Exception:
                raise RuntimeError("GitLab API error")
        else:
            return PRDiff(
                diff_content='{{"Mock GitLab diff (httpx not available)\\n\\nMR: {}\\nBase: unknown\\nHead: unknown\\n'.format(
                    pr
                )
            )

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
                        return "unknown"

                    mr_data = response.json()
                    return mr_data.get("sha", "unknown")
            except Exception:
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

        pattern = r"https://gitlab\.com/([^/]+)/([^/]+)/(merge_requests|tree)/(\d+)"
        return bool(re.match(pattern, url))
