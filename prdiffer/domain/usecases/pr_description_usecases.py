"""Use cases for PR description update operations.

This module provides business logic for updating GitHub pull request
descriptions, following Clean Architecture principles.
"""

from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.exceptions import ValidationError, InvalidURLError
from prdiffer.domain.errors import (
    E1001_INVALID_URL,
    E1009_INVALID_FORMAT,
)


class UpdatePRDescriptionUseCase:
    """Use case for updating a GitHub PR description.

    This use case orchestrates PR description update by:
    1. Validating input parameters
    2. Delegating to repository service for the update
    3. Handling errors and logging appropriately
    """

    def __init__(
        self,
        pr_diff_repository: PRDiffRepositoryInterface,
        logger: LoggerServiceInterface | None = None,
    ):
        """Initialize use case with dependencies.

        Args:
            pr_diff_repository: Repository service for PR operations
            logger: Optional logger service for DI
        """
        self._pr_diff_repository = pr_diff_repository
        self._logger = logger

    async def execute(self, pr_url: str, pr_description: str) -> str:
        """Execute PR description update.

        Args:
            pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            pr_description: The new description text for the PR

        Returns:
            str: Success message indicating PR description was updated

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If PR update fails (404, 403, rate limit, etc.)
        """
        if self._logger:
            self._logger.info(
                "Executing update PR description use case",
                pr_url=pr_url[:100],
            )

        # Validate inputs
        if not pr_url:
            raise InvalidURLError(
                "PR URL cannot be empty", error_code=E1001_INVALID_URL
            )

        if not isinstance(pr_url, str):
            raise ValidationError(
                f"PR URL must be a string, got {type(pr_url).__name__}",
                error_code=E1009_INVALID_FORMAT,
            )

        if not pr_description:
            raise ValidationError(
                "PR description cannot be empty", error_code=E1001_INVALID_URL
            )

        if not isinstance(pr_description, str):
            raise ValidationError(
                f"PR description must be a string, got {type(pr_description).__name__}",
                error_code=E1009_INVALID_FORMAT,
            )

        # Delegate to repository service for update
        # The repository handles all GitHub API interaction and error handling
        result = await self._pr_diff_repository.update_pr_description(
            pr_url=pr_url,
            description=pr_description,
        )

        if self._logger:
            self._logger.info(
                "PR description update use case completed successfully",
                result=result[:100],
            )

        return result
