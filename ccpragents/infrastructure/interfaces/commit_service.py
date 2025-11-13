"""Infrastructure interface for commit operations.

This interface defines the contract for commit-related operations at the
infrastructure layer, abstracting away the specific implementation details.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from github.Repository import Repository
from github.Commit import Commit


class CommitServiceInterface(ABC):
    """Abstract interface for commit operations."""

    @abstractmethod
    async def get_pr_commits(
        self, repository: Repository, pr_number: int
    ) -> List[Commit]:
        """Get all commits in a pull request.

        Args:
            repository: GitHub repository instance
            pr_number: Pull request number

        Returns:
            List[Commit]: List of commits in the PR

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            PullRequestNotFoundError: If PR doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_latest_commit_sha(
        self, repository: Repository, pr_number: int
    ) -> Optional[str]:
        """Get the latest commit SHA for a pull request.

        Args:
            repository: GitHub repository instance
            pr_number: Pull request number

        Returns:
            Optional[str]: Latest commit SHA if found, None otherwise

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            PullRequestNotFoundError: If PR doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_merge_base(
        self, repository: Repository, base_ref: str, head_ref: str
    ) -> Optional[str]:
        """Get the merge base commit between two references.

        Args:
            repository: GitHub repository instance
            base_ref: Base reference (branch, tag, or commit)
            head_ref: Head reference (branch, tag, or commit)

        Returns:
            Optional[str]: Merge base commit SHA if found, None otherwise

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            RefNotFoundError: If references don't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def compare_commits(
        self, repository: Repository, base_sha: str, head_sha: str
    ) -> Dict[str, any]:
        """Compare two commits and get the diff.

        Args:
            repository: GitHub repository instance
            base_sha: Base commit SHA
            head_sha: Head commit SHA

        Returns:
            Dict[str, any]: Comparison result with files changed, commits, etc.

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            CommitNotFoundError: If commits don't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_commit_messages(
        self, repository: Repository, pr_number: int
    ) -> List[str]:
        """Get commit messages for all commits in a PR.

        Args:
            repository: GitHub repository instance
            pr_number: Pull request number

        Returns:
            List[str]: List of commit messages

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            PullRequestNotFoundError: If PR doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def parse_commit_message(self, message: str) -> Dict[str, str]:
        """Parse a commit message into structured components.

        Args:
            message: Raw commit message

        Returns:
            Dict[str, str]: Parsed components (title, body, type, etc.)
        """
        pass
