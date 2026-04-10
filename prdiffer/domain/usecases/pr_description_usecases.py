"""Use cases for PR description update operations."""

from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.exceptions import ValidationError, InvalidURLError
from prdiffer.domain.errors import (
    E1001_INVALID_URL,
)


class UpdatePRDescriptionUseCase:
    """Orchestrates PR description update: validates input, delegates to repository, handles errors."""

    def __init__(
        self,
        pr_diff_repository: PRDiffRepositoryInterface,
        logger: LoggerServiceInterface | None = None,
    ):
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

        if not pr_url:
            raise InvalidURLError("PR URL cannot be empty", error_code=E1001_INVALID_URL)

        if not pr_description:
            raise ValidationError("PR description cannot be empty", error_code=E1001_INVALID_URL)

        if not isinstance(pr_description, str):
            raise ValidationError("PR description must be a string", error_code=E1001_INVALID_URL)

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
