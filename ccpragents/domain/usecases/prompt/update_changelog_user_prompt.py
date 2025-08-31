from ccpragents.domain.entities.prompt import PromptRequest, PRDetails
from ccpragents.domain.repositories import PromptRepositoryInterface


class UpdateChangelogUserPromptUseCase:
    '''Use case for generating changelog user prompts.'''

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self, pr_details: PRDetails, commit_messages: str, diff_content: str) -> str:
        '''Execute the changelog update use case.

        Args:
            pr_details: PR identification details
            commit_messages: Commit messages from the PR
            diff_content: Diff content from the PR

        Returns:
            str: AI-generated changelog entries
        '''
        request = PromptRequest(
            pr_details=pr_details,
            commit_messages=commit_messages,
            diff_content=diff_content
        )
        return await self._prompt_repository.update_changelog_user_prompt(request)