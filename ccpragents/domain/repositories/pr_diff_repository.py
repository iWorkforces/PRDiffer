"""Repository interface for PR diff operations."""

from abc import ABC, abstractmethod
from ccpragents.domain.entities.pr_diff import PRDiff


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
