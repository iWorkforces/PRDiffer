"""Domain service interface for file processing operations.

This interface defines the contract for file processing operations at the domain level,
including file filtering, content retrieval, and diff generation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ccpragents.domain.entities.file_patch import FilePatchInfo


class FileProcessingServiceInterface(ABC):
    """Abstract interface for file processing operations at the domain level."""

    @abstractmethod
    async def process_pr_files(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        max_files: Optional[int] = None,
    ) -> List[FilePatchInfo]:
        """Process all files in a pull request.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number
            max_files: Maximum number of files to process (optional)

        Returns:
            List[FilePatchInfo]: List of processed file patches

        Raises:
            RepositoryNotFoundError: If repository or PR doesn't exist
            AuthenticationError: If authentication fails
            FileProcessingError: If file processing fails
        """
        pass

    @abstractmethod
    def filter_files(
        self,
        file_paths: List[str],
        ignore_patterns: Optional[List[str]] = None,
        valid_extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """Filter files based on ignore patterns and valid extensions.

        Args:
            file_paths: List of file paths to filter
            ignore_patterns: List of patterns to ignore (optional)
            valid_extensions: List of valid file extensions (optional)

        Returns:
            List[str]: Filtered list of file paths
        """
        pass

    @abstractmethod
    async def get_file_content(
        self,
        repo_owner: str,
        repo_name: str,
        file_path: str,
        commit_sha: str,
    ) -> Optional[str]:
        """Get the content of a specific file at a commit SHA.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            file_path: Path to the file
            commit_sha: Commit SHA to get content from

        Returns:
            Optional[str]: File content if successful, None otherwise

        Raises:
            FileNotFoundError: If file doesn't exist at the commit SHA
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def generate_file_diff(
        self,
        original_content: str,
        new_content: str,
        filename: str,
    ) -> str:
        """Generate a unified diff for a file.

        Args:
            original_content: Original file content
            new_content: New file content
            filename: Name of the file

        Returns:
            str: Unified diff string

        Raises:
            DiffGenerationError: If diff generation fails
        """
        pass

    @abstractmethod
    def is_binary_file(self, content: bytes) -> bool:
        """Determine if a file is binary based on its content.

        Args:
            content: File content as bytes

        Returns:
            bool: True if the file is binary, False otherwise
        """
        pass

    @abstractmethod
    def get_file_language(self, filename: str, content: str) -> Optional[str]:
        """Detect the programming language of a file.

        Args:
            filename: Name of the file
            content: File content

        Returns:
            Optional[str]: Detected language, or None if undetermined
        """
        pass
