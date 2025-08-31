from ccpragents.domain.repositories import PromptRepositoryInterface


class ApprovePRSystemPromptUseCase:
    """Use case for generating PR approval system prompts."""

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self) -> str:
        """Execute the PR approval system prompt use case.

        Returns:
            str: System prompt for PR approval tasks
        """
        return await self._prompt_repository.approve_pr_system_prompt()