"""Use cases for PR approval operations.

This module provides business logic for approving GitHub pull requests
with compliments, following Clean Architecture principles.
"""

from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.exceptions import ValidationError, InvalidURLError
from prdiffer.domain.errors import (
    E1001_INVALID_URL,
)


class ApprovePRUseCase:
    """Use case for approving a GitHub PR with a compliment comment.

    This use case orchestrates PR approval by:
    1. Validating input parameters
    2. Delegating to repository service for approval
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

    async def execute(self, pr_url: str, compliment: str) -> str:
        """Execute PR approval with compliment.

        Args:
            pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            compliment: The compliment text to include in the approval review

        Returns:
            str: Success message indicating PR was approved

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If PR approval fails (404, 403, rate limit, etc.)
        """
        if self._logger:
            self._logger.info(
                "Executing approve PR use case",
                pr_url=pr_url[:100],
            )

        # Validate inputs
        if not pr_url:
            raise InvalidURLError("PR URL cannot be empty", error_code=E1001_INVALID_URL)

        if not compliment:
            raise ValidationError("Compliment cannot be empty", error_code=E1001_INVALID_URL)

        # Delegate to repository service for approval
        # The repository handles all GitHub API interaction and error handling
        result = await self._pr_diff_repository.approve_pr_with_comment(
            pr_url=pr_url,
            compliment=compliment,
        )

        if self._logger:
            self._logger.info(
                "PR approval use case completed successfully",
                result=result[:100],
            )

        return result
