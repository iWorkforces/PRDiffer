"""Infrastructure implementation of PRDiffServiceInterface.

This module provides the concrete implementation of PRDiffServiceInterface
using GitHub API operations.
"""

from typing import Optional

from ccpragents.domain.services.pr_diff_service import PRDiffServiceInterface
from ccpragents.domain.entities.pr_diff import PRDiff
from ccpragents.infrastructure.github.api_client import GitHubAPIClient


class GitHubPRDiffService(PRDiffServiceInterface):
    """Concrete implementation of PRDiffServiceInterface using GitHub API."""

    def __init__(self, github_api_client: Optional[GitHubAPIClient] = None):
        """Initialize the service with GitHub API client.

        Args:
            github_api_client: Optional GitHub API client (created if None)
        """
        self._github_api = github_api_client or GitHubAPIClient()

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
        try:
            # Use the GitHub API client to get repository and PR
            repository = self._github_api.get_repository(repo_owner, repo_name)
            if not repository:
                return None

            pull_request = self._github_api.get_pull_request(repository, pr_number)
            if not pull_request:
                return None

            # Get the files in the PR
            files = self._github_api.get_pr_files(pull_request)

            # Get the latest commit SHA
            latest_commit_sha = self.get_latest_commit_sha(
                repo_owner, repo_name, pr_number
            )

            # Create PRDiff entity
            pr_diff = PRDiff(
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                pr_title=pull_request.title or "",
                pr_body=pull_request.body or "",
                author=pull_request.user.login if pull_request.user else "",
                created_at=pull_request.created_at.isoformat()
                if pull_request.created_at
                else "",
                updated_at=pull_request.updated_at.isoformat()
                if pull_request.updated_at
                else "",
                merged_at=pull_request.merged_at.isoformat()
                if pull_request.merged_at
                else "",
                closed_at=pull_request.closed_at.isoformat()
                if pull_request.closed_at
                else "",
                state="merged"
                if pull_request.merged
                else ("closed" if pull_request.closed_at else "open"),
                draft=pull_request.draft or False,
                mergeable=pull_request.mergeable,
                additions=pull_request.additions or 0,
                deletions=pull_request.deletions or 0,
                changed_files=pull_request.changed_files or 0,
                commit_sha=latest_commit_sha or "",
                files=files,
                commits=[],
            )

            return pr_diff

        except Exception as e:
            # Log the error and return None for graceful degradation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to get PR diff - repo: %s/%s, pr: %s, error: %s (%s)",
                repo_owner,
                repo_name,
                pr_number,
                str(e),
                type(e).__name__,
            )
            return None

    def get_latest_commit_sha(
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
        try:
            repository = self._github_api.get_repository(repo_owner, repo_name)
            if not repository:
                return None

            pull_request = self._github_api.get_pull_request(repository, pr_number)
            if not pull_request:
                return None

            # Get the latest commit from the PR
            commits = list(pull_request.get_commits())
            if not commits:
                return None

            # Return the SHA of the latest commit
            latest_commit = commits[-1]
            return latest_commit.sha if latest_commit else None

        except Exception as e:
            # Log the error and return None for graceful degradation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to get latest commit SHA - repo: %s/%s, pr: %s, error: %s (%s)",
                repo_owner,
                repo_name,
                pr_number,
                str(e),
                type(e).__name__,
            )
            return None

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
        try:
            repository = self._github_api.get_repository(repo_owner, repo_name)
            return repository is not None
        except Exception as e:
            # Log the error and return False for graceful degradation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to validate repository access - repo: %s/%s, error: %s (%s)",
                repo_owner,
                repo_name,
                str(e),
                type(e).__name__,
            )
            return False
