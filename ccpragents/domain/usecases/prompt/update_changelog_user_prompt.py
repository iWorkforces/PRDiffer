from ccpragents.domain.entities.prompt import PromptRequest, PRDetails
from ccpragents.domain.repositories import PromptRepositoryInterface


class UpdateChangelogUserPromptUseCase:
    '''Use case for generating changelog user prompts.'''

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self, pr_details: PRDetails, pr_commit_messages: str, pr_diff: str) -> str:
        '''Execute the changelog update use case.

        Args:
            pr_details: PR identification details
            pr_commit_messages: Commit messages from the PR
            pr_diff: Diff content from the PR

        Returns:
            str: AI-generated changelog entries
        '''
        request = PromptRequest(
            pr_details=pr_details,
            pr_commit_messages=pr_commit_messages,
            pr_diff=pr_diff
        )
        return await self._prompt_repository.update_changelog_user_prompt(request)