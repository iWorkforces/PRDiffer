"""Application service for PR diff operations.

This service provides the application layer orchestration for PR diff
operations, coordinating between use cases, infrastructure services,
and presentation logic.
"""

from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from ccpragents.domain.entities.pr_diff import PRDiff
from ccpragents.domain.entities.file_patch import FilePatchInfo
from ccpragents.domain.usecases import GetPRDiffUseCase
from ccpragents.domain.services.logger import LoggerServiceInterface
from ccpragents.domain.services.settings import SettingsServiceInterface


class PRDiffApplicationServiceInterface(ABC):
    """Abstract interface for PR diff application service."""

    @abstractmethod
    async def get_pr_diff(self, pr_url: str) -> PRDiff:
        """Get PR diff data for the specified URL.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            PRDiff: Complete PR diff information

        Raises:
            ValidationError: If URL is invalid
            RepositoryNotFoundError: If repository or PR doesn't exist
            ServiceError: If service operation fails
        """
        pass

    @abstractmethod
    async def get_pr_diff_summary(self, pr_url: str) -> Dict[str, Any]:
        """Get a summary of the PR diff.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            Dict[str, Any]: PR summary with key metrics
        """
        pass

    @abstractmethod
    async def get_file_analysis(self, pr_url: str) -> List[Dict[str, Any]]:
        """Get analysis of all files in the PR.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            List[Dict[str, Any]]: List of file analysis results
        """
        pass

    @abstractmethod
    def validate_pr_url(self, pr_url: str) -> bool:
        """Validate a PR URL format.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            bool: True if URL is valid format
        """
        pass


class PRDiffApplicationService(PRDiffApplicationServiceInterface):
    """Concrete implementation of PR diff application service."""

    def __init__(
        self,
        settings_service: SettingsServiceInterface,
        logger: LoggerServiceInterface,
    ):
        """Initialize the application service.

        Args:
            settings_service: Settings service for configuration
            logger: Logger service for structured logging
        """
        self._settings_service = settings_service
        self._logger = logger

    async def get_pr_diff(self, pr_url: str) -> PRDiff:
        """Get PR diff data for the specified URL.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            PRDiff: Complete PR diff information

        Raises:
            ValidationError: If URL is invalid
            RepositoryNotFoundError: If repository or PR doesn't exist
            ServiceError: If service operation fails
        """
        # Extract repository information from URL
        repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)

        self._logger.info(
            "Fetching PR diff",
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            pr_url=pr_url
        )

        try:
            # TODO: Create and execute use case with proper dependencies
            # This would require the infrastructure factory to be properly integrated
            # For now, return a placeholder PRDiff
            pr_diff = PRDiff(
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                pr_title="Sample PR Title",
                pr_body="Sample PR description",
                author="sample-author",
                state="open",
                additions=10,
                deletions=5,
                changed_files=3,
                commit_sha="abc123def456",
                files=[
                    FilePatchInfo(
                        filename="src/main.py",
                        patch="@@ -1,3 +1,3 @@\n old content\n+new content\n",
                        edit_type="modified",
                        num_plus_lines=1,
                        num_minus_lines=1,
                        language="python"
                    )
                ]
            )

            self._logger.info(
                "Successfully fetched PR diff",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                files_count=len(pr_diff.files),
                total_changes=pr_diff.get_total_changes()
            )

            return pr_diff

        except Exception as e:
            self._logger.error(
                "Failed to fetch PR diff",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def get_pr_diff_summary(self, pr_url: str) -> Dict[str, Any]:
        """Get a summary of the PR diff.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            Dict[str, Any]: PR summary with key metrics
        """
        try:
            pr_diff = await self.get_pr_diff(pr_url)
            return pr_diff.get_summary()
        except Exception as e:
            self._logger.error(
                "Failed to get PR diff summary",
                pr_url=pr_url,
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "error": f"Failed to get PR diff summary: {e}",
                "pr_url": pr_url
            }

    async def get_file_analysis(self, pr_url: str) -> List[Dict[str, Any]]:
        """Get analysis of all files in the PR.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            List[Dict[str, Any]]: List of file analysis results
        """
        try:
            pr_diff = await self.get_pr_diff(pr_url)
            return [file.get_summary() for file in pr_diff.files]
        except Exception as e:
            self._logger.error(
                "Failed to get file analysis",
                pr_url=pr_url,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    def validate_pr_url(self, pr_url: str) -> bool:
        """Validate a PR URL format.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            bool: True if URL is valid format
        """
        import re

        # GitHub PR URL pattern
        pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, pr_url)

        if not match:
            return False

        repo_owner, repo_name, pr_number = match.groups()

        # Additional validation
        if not repo_owner or not repo_name:
            return False

        if len(repo_owner) > 100 or len(repo_name) > 100:
            return False

        try:
            pr_num = int(pr_number)
            if pr_num <= 0:
                return False
        except ValueError:
            return False

        return True

    def _parse_pr_url(self, pr_url: str) -> tuple[str, str, int]:
        """Parse GitHub PR URL to extract repository and PR information.

        Args:
            pr_url: GitHub pull request URL

        Returns:
            tuple[str, str, int]: (repo_owner, repo_name, pr_number)

        Raises:
            ValueError: If URL format is invalid
        """
        import re

        pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, pr_url)

        if not match:
            raise ValueError(f"Invalid GitHub PR URL format: {pr_url}")

        repo_owner, repo_name, pr_number_str = match.groups()

        try:
            pr_number = int(pr_number_str)
        except ValueError:
            raise ValueError(f"Invalid PR number: {pr_number_str}")

        return repo_owner, repo_name, pr_number