"""Infrastructure interface for GitHub file operations.

This interface defines the contract for file-related operations at the
infrastructure layer, abstracting away the specific GitHub API implementation.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from github.Repository import Repository
from github.ContentFile import ContentFile


class GitHubFileServiceInterface(ABC):
    """Abstract interface for GitHub file operations."""

    @abstractmethod
    async def get_pr_files(self, repository: Repository, pull_request_number: int) -> List[ContentFile]:
        """Get all files changed in a pull request.

        Args:
            repository: GitHub repository instance
            pull_request_number: Pull request number

        Returns:
            List[ContentFile]: List of files changed in the PR

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            PullRequestNotFoundError: If PR doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_file_content(self, repository: Repository, file_path: str, ref: str) -> Optional[str]:
        """Get the content of a specific file.

        Args:
            repository: GitHub repository instance
            file_path: Path to the file
            ref: Branch, tag, or commit SHA

        Returns:
            Optional[str]: File content if found, None otherwise

        Raises:
            FileNotFoundError: If file doesn't exist at the specified ref
            RepositoryNotFoundError: If repository doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def batch_get_file_content(
        self,
        repository: Repository,
        file_paths: List[str],
        ref: str
    ) -> Dict[str, Optional[str]]:
        """Get content for multiple files efficiently.

        Args:
            repository: GitHub repository instance
            file_paths: List of file paths to retrieve
            ref: Branch, tag, or commit SHA

        Returns:
            Dict[str, Optional[str]]: Mapping of file paths to content

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_file_at_commit(
        self,
        repository: Repository,
        file_path: str,
        commit_sha: str
    ) -> Optional[str]:
        """Get file content at a specific commit.

        Args:
            repository: GitHub repository instance
            file_path: Path to the file
            commit_sha: Commit SHA

        Returns:
            Optional[str]: File content at the commit if found, None otherwise

        Raises:
            FileNotFoundError: If file doesn't exist at the commit
            RepositoryNotFoundError: If repository doesn't exist
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def is_file_binary(self, content: bytes) -> bool:
        """Determine if file content represents a binary file.

        Args:
            content: File content as bytes

        Returns:
            bool: True if the file is binary, False if text
        """
        pass