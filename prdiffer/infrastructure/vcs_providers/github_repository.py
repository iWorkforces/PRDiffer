"""GitHub VCS provider implementation.

This module implements the existing PRDiffRepositoryInterface for GitHub,
ensuring backward compatibility with existing code while providing
a foundation for the new VCS provider abstraction.
"""

from typing import Optional
from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.entities.pr_diff import PRDiff

from prdiffer.infrastructure.github_repository import GitHubPRDiffRepository


class GitHubVCSRepository(PRDiffRepositoryInterface):
    """GitHub-specific implementation extending PRDiffRepositoryInterface.

    This class wraps the existing GitHubPRDiffRepository functionality
    to maintain backward compatibility while enabling multi-provider support.
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None,
    ):
        """Initialize GitHub VCS repository.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number
            github_token: GitHub personal access token
        """
        self._repo_owner = repo_owner
        self._repo_name = repo_name
        self._pr_number = pr_number
        self._github_token = github_token or None

        self._inner_repo = GitHubPRDiffRepository(
            repo_owner, repo_name, pr_number, github_token
        )

    @property
    def repo_owner(self) -> str:
        """Repository owner/organization name."""
        return self._inner_repo.repo_owner

    @property
    def repo_name(self) -> str:
        """Repository name."""
        return self._inner_repo.repo_name

    @property
    def pr_number(self) -> int:
        """Pull request number."""
        return self._inner_repo.pr_number

    async def initialize(self) -> None:
        """Initialize GitHub repository connection."""
        await self._inner_repo.initialize()

    async def get_pr_diff(self) -> PRDiff:
        """Get PR diff from GitHub.

        Returns:
            PRDiff: Complete PR diff with file context
        """
        return await self._inner_repo.get_pr_diff()

    async def get_latest_commit_sha(self) -> str:
        """Get latest head commit SHA for PR."""
        return await self._inner_repo.get_latest_commit_sha()

    async def approve_pr_with_comment(self, pr_url: str, compliment: str) -> str:
        """Approve a GitHub PR with a compliment comment.

        This method delegates to the inner repository to approve the PR.

        Args:
            pr_url: The full GitHub PR URL
            compliment: The compliment text to include in the approval review

        Returns:
            str: Success message indicating PR was approved

        Raises:
            InvalidURLError: If PR URL format is invalid
            RuntimeError: If GitHub objects failed to initialize
            GithubException: If PR approval fails
        """
        return await self._inner_repo.approve_pr_with_comment(pr_url, compliment)

    def supports_repository(self, url: str) -> bool:
        """Check if URL belongs to GitHub.

        Args:
            url: Repository URL

        Returns:
            bool: True if GitHub supports this URL
        """
        import re

        pattern = r"https://github\.com/([^/]+)/([^/]+)/(pull|tree)/(\d+)"
        return bool(re.match(pattern, url))


def get_github_vcs_repository(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
    github_token: Optional[str] = None,
) -> GitHubVCSRepository:
    """Get GitHub VCS repository instance.

    This factory function creates a GitHubVCSRepository instance,
    maintaining compatibility with existing code patterns.

    Args:
        repo_owner: Repository owner/organization
        repo_name: Repository name
        pr_number: Pull request number
        github_token: GitHub personal access token

    Returns:
        GitHubVCSRepository: GitHub VCS provider instance
    """
    return GitHubVCSRepository(repo_owner, repo_name, pr_number, github_token)
