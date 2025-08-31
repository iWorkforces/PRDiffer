from ccpragents.domain.repositories import PromptRepositoryInterface


class ReviewPRSystemPromptUseCase:
    """Use case for generating PR review system prompts."""

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self) -> str:
        """Execute the PR review system prompt use case.

        Returns:
            str: System prompt for PR review tasks
        """
        return await self._prompt_repository.review_pr_system_prompt()