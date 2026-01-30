"""PR operation handler component for GitHub PR-related operations."""

from typing import Dict, Any, Optional, Callable

from prdiffer.domain.interfaces.protocols import PROperationHandlerProtocol
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.exceptions import (
    InvalidPRNumberError,
    InvalidRepositoryError,
    InvalidURLError,
    SuspiciousOperationError,
)
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.application.utils.pr_url_parser import parse_pr_url


class PROperationHandler(PROperationHandlerProtocol):
    """Component responsible for handling PR-related operations."""

    def __init__(
        self,
        github_repository_class: Callable[[str, str, int], PRDiffRepositoryInterface],
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        logger: LoggerServiceInterface,
        input_validator: Optional[InputValidator] = None,
    ):
        """Initialize PR operation handler.

        Args:
            github_repository_class: Callable that creates GitHub repository instances
            cache_service: Cache service for storing PR data
            repository_cache_service: Repository cache service
            logger: Logger service instance (injected via dependency inversion)
        """
        self._github_repository_class = github_repository_class
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._logger = logger
        self._input_validator = input_validator or InputValidator()

    async def get_pr_diff(self, pr_url: str) -> Dict[str, Any]:
        """Get PR diff information.

        Automatic commit-based caching ensures fresh data is returned when PR changes.
        Returns structured files array response for file-level diff analysis.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            api_key: Optional API key for authentication (required if auth enabled)

        Returns:
            Dictionary containing structured files array with per-file metadata
            Each file includes: path, status, stats (additions/deletions), diff

        Raises:
            ValueError: If URL format is invalid
            RuntimeError: If PR diff fetch fails

        Note:
            Breaking Change: Response now uses files array instead of concatenated diff_content string.
            File metadata: path, status (added/modified/deleted/renamed/unknown),
                           stats (additions, deletions), diff (full patch content)
        """
        try:
            # Validate input
            if not pr_url:
                raise ValueError("PR URL parameter is required")

            # Parse URL to extract repository details
            try:
                repo_owner, repo_name, pr_number = parse_pr_url(
                    pr_url, self._input_validator
                )
            except (
                InvalidURLError,
                InvalidRepositoryError,
                InvalidPRNumberError,
                SuspiciousOperationError,
            ) as exc:
                raise ValueError(
                    f"Invalid GitHub PR URL format. Expected format: "
                    f"https://github.com/owner/repo/pull/123, got: {pr_url}"
                ) from exc

            # Try to get repository from cache first
            cached_repository: Optional[PRDiffRepositoryInterface] = (
                self._repository_cache_service.retrieve(
                    repo_owner, repo_name, pr_number
                )
            )

            repository: PRDiffRepositoryInterface
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
