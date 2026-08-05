"""GitHub API service interface for domain layer."""

from abc import ABC, abstractmethod

from prdiffer.domain.entities.file_content import FileContentResult
from prdiffer.domain.entities.pull_request import PullRequest
from prdiffer.domain.entities.repository import Repository


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
    def get_file_content(self, repo_full_name: str, file_path: str, branch: str) -> FileContentResult:
        """Get typed file content from a specific branch/ref.

        Returns:
            FileContentAvailable for successful text (including empty string),
            or FileContentUnavailable for deterministic content limitations.

        Raises:
            Operational provider exceptions (auth, rate limit, transport, retry exhaustion)
            rather than mapping them into FileContentUnavailable.
        """
        pass

    @abstractmethod
    def get_files_content_batch(
        self,
        repo_full_name: str,
        file_paths: list[str],
        branch: str,
    ) -> dict[str, FileContentResult]:
        """Batch retrieve typed file contents from a specific branch/ref.

        Returns:
            Mapping of path → FileContentResult. Only available texts are cached.
        """
        pass
