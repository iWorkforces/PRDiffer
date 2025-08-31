'''GitHub API service interface for domain layer.'''
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from github.Repository import Repository
from github.PullRequest import PullRequest


class GitHubAPIServiceInterface(ABC):
    '''Abstract base class for GitHub API services.

    This interface defines the contract for services that provide
    GitHub API interactions for repository and pull request operations.
    '''

    @abstractmethod
    def initialize_client(self, github_token: Optional[str] = None, timeout: int = 30) -> None:
        '''Initialize the GitHub client with authentication.

        Args:
            github_token: GitHub personal access token for authentication
            timeout: API timeout in seconds
        '''
        pass

    @abstractmethod
    def get_repository(self, repo_full_name: str) -> Optional[Repository]:
        '''Get a GitHub repository instance.

        Args:
            repo_full_name: Repository full name in format "owner/repo"

        Returns:
            Repository instance if found, None otherwise
        '''
        pass

    @abstractmethod
    def get_pull_request(self, repository: Repository, pr_number: int) -> Optional[PullRequest]:
        '''Get a pull request instance.

        Args:
            repository: GitHub repository instance
            pr_number: Pull request number

        Returns:
            PullRequest instance if found, None otherwise
        '''
        pass

    @abstractmethod
    def get_file_content(self, repository: Repository, file_path: str, branch: str) -> str:
        '''Get file content from a specific branch.

        Args:
            repository: GitHub repository instance
            file_path: Path to the file in the repository
            branch: Branch or commit SHA

        Returns:
            str: File content as string, empty string on error
        '''
        pass

    @abstractmethod
    def get_files_content_batch(self, repository: Repository, file_paths: List[str], branch: str) -> Dict[str, str]:
        '''Batch retrieve file contents from a specific branch.

        Args:
            repository: GitHub repository instance
            file_paths: List of file paths to retrieve
            branch: Branch or commit SHA

        Returns:
            Dict mapping file paths to their content (empty string on error)
        '''
        pass
