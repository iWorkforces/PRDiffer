"""PR operation handler component for GitHub PR-related operations."""

import re
from typing import Dict, Any, Optional, Tuple

from prdiffer.domain.interfaces.protocols import PROperationHandlerProtocol
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface


class PROperationHandler(PROperationHandlerProtocol):
    """Component responsible for handling PR-related operations."""

    def __init__(
        self,
        github_repository_class,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        logger: LoggerServiceInterface,
    ):
        """Initialize PR operation handler.

        Args:
            github_repository_class: Class for creating GitHub repository instances
            cache_service: Cache service for storing PR data
            repository_cache_service: Repository cache service
            logger: Logger service instance (injected via dependency inversion)
        """
        self._github_repository_class = github_repository_class
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._logger = logger

    def _parse_pr_url(self, pr_url: str) -> Tuple[str, str, int]:
        """Parse GitHub PR URL to extract repository and PR information.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            Tuple of (repo_owner, repo_name, pr_number)

        Raises:
            ValueError: If URL format is invalid
        """
        pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, pr_url)

        if not match:
            raise ValueError(
                f"Invalid GitHub PR URL format. Expected format: "
                f"https://github.com/owner/repo/pull/123, got: {pr_url}"
            )

        repo_owner = match.group(1)
        repo_name = match.group(2)
        pr_number = int(match.group(3))

        return repo_owner, repo_name, pr_number

    async def get_pr_diff(self, pr_url: str) -> Dict[str, Any]:
        """Get PR diff information.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            Dictionary containing PR diff data

        Raises:
            ValueError: If URL format is invalid
            RuntimeError: If PR diff fetch fails

        Note:
            Caching is automatic and always enabled based on commit SHA invalidation.
        """
        try:
            # Validate input
            if not pr_url:
                raise ValueError("PR URL parameter is required")

            # Parse URL to extract repository details
            repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)

            # Try to get repository from cache first
            cached_repository: Optional[PRDiffRepositoryInterface] = (
                self._repository_cache_service.retrieve(
                    repo_owner, repo_name, pr_number
                )
            )

            if cached_repository is None:
                # Create new repository instance
                repository = self._github_repository_class(
                    repo_owner, repo_name, pr_number
                )
                self._logger.debug(
                    "Created new repository instance",
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    pr_number=pr_number,
                )
            else:
                self._logger.debug(
                    "Reusing cached repository instance",
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    pr_number=pr_number,
                )
                repository = cached_repository

            # Execute use case with automatic caching
            # repository is guaranteed to be set at this point

            # Initialize the repository with settings
            if hasattr(repository, "initialize") and callable(repository.initialize):
                await repository.initialize()

            # Execute the repository directly (since we don't have a PRDiffService)
            pr_diff: Optional[PRDiff] = await repository.get_pr_diff()

            # Handle case where repository returns None
            if pr_diff is None:
                self._logger.error(
                    "Repository returned None for PR diff",
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    pr_number=pr_number,
                )
                raise ValueError("Failed to get PR diff - repository returned None")

            # Cache the repository after it's been used (now it should be initialized)
            if hasattr(repository, "_initialized") and getattr(
                repository, "_initialized", False
            ):
                cache_success = self._repository_cache_service.insert(repository)
                if cache_success:
                    self._logger.debug(
                        "Cached repository instance after initialization",
                        repo_owner=repo_owner,
                        repo_name=repo_name,
                        pr_number=pr_number,
                    )

            response = pr_diff.model_dump()
            self._logger.info(
                "Successfully fetched PR diff",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
            )
            return response

        except ValueError as e:
            # Validation errors - provide clear error messages
            self._logger.warning(
                "Validation error in PR diff request",
                pr_url=pr_url,
                error=str(e),
            )
            raise ValueError(f"Invalid request: {e}")

        except Exception as e:
            # GitHub API or other unexpected errors
            self._logger.error(
                "Failed to fetch PR diff",
                pr_url=pr_url,
                error=str(e),
            )
            # Re-raise with consistent error format
            raise RuntimeError(f"Failed to fetch PR diff: {e}")

    async def describe_pr(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Generate PR description based on commit messages and diff.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR (unused in current implementation)
            diff_content: Diff content of the PR

        Returns:
            Generated PR description

        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        # Parameters are part of protocol interface but not used in stub implementation
        _ = commit_messages, diff_content  # Mark as intentionally unused
        raise NotImplementedError(
            "PR description generation is not yet implemented. "
            "This feature is planned for a future release."
        )

    async def approve_pr(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Generate PR approval message.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR (unused in current implementation)
            diff_content: Diff content of the PR

        Returns:
            Generated approval message

        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        # Parameters are part of protocol interface but not used in stub implementation
        _ = commit_messages, diff_content  # Mark as intentionally unused
        raise NotImplementedError(
            "PR approval generation is not yet implemented. "
            "This feature is planned for a future release."
        )

    async def review_pr(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Generate PR review.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR (unused in current implementation)
            diff_content: Diff content of the PR

        Returns:
            Generated PR review

        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        # Parameters are part of protocol interface but not used in stub implementation
        _ = commit_messages, diff_content  # Mark as intentionally unused
        raise NotImplementedError(
            "PR review generation is not yet implemented. "
            "This feature is planned for a future release."
        )

    async def update_pr_changelog(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Update PR changelog.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR (unused in current implementation)
            diff_content: Diff content of the PR

        Returns:
            Updated changelog content

        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        # Parameters are part of protocol interface but not used in stub implementation
        _ = commit_messages, diff_content  # Mark as intentionally unused
        raise NotImplementedError(
            "PR changelog update is not yet implemented. "
            "This feature is planned for a future release."
        )
