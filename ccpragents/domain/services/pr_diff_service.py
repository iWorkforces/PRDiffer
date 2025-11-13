"""Domain service interface for PR diff operations.

This interface defines the contract for PR diff operations at the domain level,
abstracting away infrastructure-specific details and providing a clean
dependency for use cases.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ccpragents.domain.entities.pr_diff import PRDiff


class PRDiffServiceInterface(ABC):
    """Abstract interface for PR diff operations at the domain level."""

    @abstractmethod
    async def get_pr_diff(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[PRDiff]:
        """Get PR diff data for the specified repository and PR.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[PRDiff]: PR diff data if successful, None otherwise

        Raises:
            RepositoryNotFoundError: If repository or PR doesn't exist
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            ValidationError: If input parameters are invalid
        """
        pass

    @abstractmethod
    async def get_latest_commit_sha(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[str]:
        """Get the latest head commit SHA for the pull request.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[str]: Latest commit SHA if successful, None otherwise

        Raises:
            RepositoryNotFoundError: If repository or PR doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def validate_repository_access(
        self,
        repo_owner: str,
        repo_name: str,
    ) -> bool:
        """Validate that the repository exists and is accessible.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name

        Returns:
            bool: True if repository is accessible, False otherwise
        """
        pass
