from ccpragents.domain.repositories import PromptRepositoryInterface


class DescribePRSystemPromptUseCase:
    """Use case for generating PR description system prompts."""

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self) -> str:
        """Execute the PR description system prompt use case.

        Returns:
            str: System prompt for PR description tasks
        """
        return await self._prompt_repository.describe_pr_system_prompt()
