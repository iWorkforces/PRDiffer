"""Repository interface for PR diff operations."""

from abc import ABC, abstractmethod
from prdiffer.domain.entities.pr_diff import PRDiff


class PRDiffRepositoryInterface(ABC):
    """Abstract interface for PR diff repository operations."""

    @property
    @abstractmethod
    def repo_owner(self) -> str:
        """Repository owner/organization name.

        Returns:
            str: The repository owner/organization name
        """
        pass

    @property
    @abstractmethod
    def repo_name(self) -> str:
        """Repository name.

        Returns:
            str: The repository name
        """
        pass

    @property
    @abstractmethod
    def pr_number(self) -> int:
        """Pull request number.

        Returns:
            int: The pull request number
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the repository.

        This method should be called before any operations to set up
        the repository connection and validate access.

        Raises:
            RuntimeError: If initialization fails (e.g., repository not accessible)
        """
        pass

    @abstractmethod
    async def get_pr_diff(self) -> PRDiff:
        """Get the PR diff data.

        Returns:
            PRDiff: The PR diff data
        """
        pass

    @abstractmethod
    async def get_latest_commit_sha(self) -> str:
        """Get the latest head commit SHA for the pull request.

        Returns:
            str: The latest head commit SHA
        """
        pass

    @abstractmethod
    async def approve_pr_with_comment(self, pr_url: str, compliment: str) -> str:
        """Approve a GitHub PR with a compliment comment.

        This method:
        1. Parses PR URL to extract owner, repo, and PR number
        2. Validates PR exists and is accessible
        3. Calls pr.create_review() with event="APPROVE" and compliment as body
        4. Returns success message or raises exceptions loudly on failures

        Args:
            pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            compliment: The compliment text to include in the approval review

        Returns:
            str: Success message indicating PR was approved

        Raises:
            InvalidURLError: If PR URL format is invalid
            RuntimeError: If GitHub objects failed to initialize
            GithubException: If PR approval fails (404, 403, rate limit, etc.)
        """
        pass
