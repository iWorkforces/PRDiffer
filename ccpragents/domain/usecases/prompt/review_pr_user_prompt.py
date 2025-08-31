from ccpragents.domain.entities.prompt import PromptRequest, PRDetails
from ccpragents.domain.repositories import PromptRepositoryInterface


class ReviewPRUserPromptUseCase:
    '''Use case for generating PR review user prompts.'''

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self, pr_details: PRDetails, commit_messages: str, diff_content: str) -> str:
        '''Execute the PR review use case.

        Args:
            pr_details: PR identification details
            commit_messages: Commit messages from the PR
            diff_content: Diff content from the PR

        Returns:
            str: AI-generated review comments and suggestions
        '''
        request = PromptRequest(
            pr_details=pr_details,
            commit_messages=commit_messages,
            diff_content=diff_content
        )
        return await self._prompt_repository.review_pr_user_prompt(request)