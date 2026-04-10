"""Use cases for PR approval operations."""

from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.exceptions import ValidationError, InvalidURLError
from prdiffer.domain.errors import (
    E1001_INVALID_URL,
)


class ApprovePRUseCase:
    """Approves a GitHub PR with a compliment comment."""

    def __init__(
        self,
        pr_diff_repository: PRDiffRepositoryInterface,
        logger: LoggerServiceInterface | None = None,
    ):
        self._pr_diff_repository = pr_diff_repository
        self._logger = logger

    async def execute(self, pr_url: str, compliment: str) -> str:
        """Execute PR approval with compliment.

        Args:
            pr_url: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            compliment: Compliment text to include in the approval review

        Returns:
            Success message indicating PR was approved

        Raises:
            InvalidURLError: If pr_url is empty
            ValidationError: If compliment is invalid
        """
        if self._logger:
            self._logger.info(
                "Executing approve PR use case",
                pr_url=pr_url[:100],
            )

        if not pr_url:
            raise InvalidURLError("PR URL cannot be empty", error_code=E1001_INVALID_URL)

        if not compliment:
            raise ValidationError("Compliment cannot be empty", error_code=E1001_INVALID_URL)

        if not isinstance(compliment, str):
            raise ValidationError("Compliment must be a string", error_code=E1001_INVALID_URL)

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
