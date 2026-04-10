"""GitHub API service interface for domain layer."""

from abc import ABC, abstractmethod

from prdiffer.domain.entities.repository import Repository
from prdiffer.domain.entities.pull_request import PullRequest


class GitHubAPIServiceInterface(ABC):
    """Abstract base class for GitHub API services.

    This interface defines the contract for services that provide
    GitHub API interactions for repository and pull request operations.
    """

    @abstractmethod
    def initialize_client(self, github_token: str | None = None, timeout: int = 30) -> None:
        """Initialize the GitHub client with authentication.

        Args:
            github_token: GitHub personal access token for authentication
            timeout: API timeout in seconds
        """
        pass

    @abstractmethod
    def get_repository(self, repo_full_name: str) -> Repository | None:
        """Get a GitHub repository instance.

        Args:
            repo_full_name: Repository full name in format "owner/repo"

        Returns:
            Repository instance if found, None otherwise
        """
        pass

    @abstractmethod
    def get_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequest | None:
        """Get a pull request instance.

        Args:
            repo_full_name: Repository full name in format "owner/repo"
            pr_number: Pull request number

        Returns:
            PullRequest instance if found, None otherwise
        """
        pass

    @abstractmethod
    def get_file_content(self, repo_full_name: str, file_path: str, branch: str) -> str:
        """Get file content from a specific branch.

        Args:
            repo_full_name: Repository full name in format "owner/repo"
            file_path: Path to the file in the repository
            branch: Branch or commit SHA

        Returns:
            str: File content as string, empty string on error
        """
        pass

    @abstractmethod
    def get_files_content_batch(self, repo_full_name: str, file_paths: list[str], branch: str) -> dict[str, str]:
        """Batch retrieve file contents from a specific branch.

        Args:
            repo_full_name: Repository full name in format "owner/repo"
            file_paths: List of file paths to retrieve
            branch: Branch or commit SHA

        Returns:
            Dict mapping file paths to their content (empty string on error)
        """
        pass
