"""PR operation handler component for GitHub PR-related operations."""

from typing import Dict, Any, Optional

from ..interfaces.protocols import PROperationHandlerProtocol
from ccpragents.domain.entities.pr_diff import PRDiff
from ccpragents.domain.usecases import GetPRDiffUseCase
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class PROperationHandler(PROperationHandlerProtocol):
    """Component responsible for handling PR-related operations."""

    def __init__(
        self,
        github_repository_class,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        logger: Optional[Any] = None,
    ):
        """Initialize PR operation handler.

        Args:
            github_repository_class: Class for creating GitHub repository instances
            cache_service: Cache service for storing PR data
            repository_cache_service: Repository cache service
            logger: Optional logger instance
        """
        self._github_repository_class = github_repository_class
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._logger = logger or get_logger()

    async def get_pr_diff(
        self,
        pr_url: str,
        use_cache: bool = True,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        pr_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get PR diff information.

        Args:
            pr_url: GitHub PR URL
            use_cache: Whether to use caching
            repo_owner: Repository owner (extracted from URL if not provided)
            repo_name: Repository name (extracted from URL if not provided)
            pr_number: PR number (extracted from URL if not provided)

        Returns:
            Dictionary containing PR diff data
        """
        try:
            # Validate input parameters
            if not pr_url:
                raise ValueError("PR URL parameter is required")

            if not isinstance(use_cache, bool):
                raise ValueError("use_cache parameter must be a boolean")

            # Use provided repo details or parse from URL
            if not all([repo_owner, repo_name, pr_number]):
                # This would need URL parsing logic - delegated to URL validator
                raise ValueError("Repository details must be provided")

            # After validation, these values are guaranteed to be non-None
            assert repo_owner is not None
            assert repo_name is not None
            assert pr_number is not None

            # Try to get repository from cache first
            repository: Optional[PRDiffRepositoryInterface] = (
                self._repository_cache_service.retrieve(
                    repo_owner, repo_name, pr_number
                )
            )

            if repository is None:
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

            # At this point, repository is guaranteed to be non-None
            assert repository is not None

            use_case: GetPRDiffUseCase = GetPRDiffUseCase(
                repository, cache_service=self._cache_service
            )
            pr_diff: PRDiff = await use_case.execute(
                use_cache=use_cache
            )  # Async execution

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
            self._logger.info("Successfully fetched PR diff")
            return response

        except ValueError as e:
            # Validation errors - provide clear error messages
            self._logger.warning(
                "Validation error in PR diff request",
                pr_url=pr_url,
                error=str(e),
                use_cache=use_cache,
            )
            raise ValueError(f"Invalid request: {e}")

        except Exception as e:
            # GitHub API or other unexpected errors
            self._logger.error(
                "Failed to fetch PR diff",
                pr_url=pr_url,
                error=str(e),
                use_cache=use_cache,
            )
            # Re-raise with consistent error format
            raise RuntimeError(f"Failed to fetch PR diff: {e}")
