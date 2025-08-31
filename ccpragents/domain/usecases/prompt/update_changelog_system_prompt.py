from ccpragents.domain.repositories import PromptRepositoryInterface


class UpdateChangelogSystemPromptUseCase:
    '''Use case for generating changelog system prompts.'''

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self) -> str:
        '''Execute the changelog system prompt use case.

        Returns:
            str: System prompt for changelog generation tasks
        '''
        return await self._prompt_repository.update_changelog_system_prompt()