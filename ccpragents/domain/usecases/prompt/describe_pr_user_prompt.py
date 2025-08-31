from fastmcp.prompts import PromptMessage
from ccpragents.domain.entities.prompt import PromptRequest, PRDetails
from ccpragents.domain.repositories import PromptRepositoryInterface


class DescribePRUserPromptUseCase:
    """Use case for generating PR description user prompts."""

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self, pr_details: PRDetails, pr_commit_messages: str, pr_diff: str) -> PromptMessage:
        """Execute the PR description use case.

        Args:
            pr_details: PR identification details
            pr_commit_messages: Commit messages from the PR
            pr_diff: Diff content from the PR

        Returns:
            str: AI-generated description of the PR changes
        """
        request = PromptRequest(
            pr_details=pr_details,
            pr_commit_messages=pr_commit_messages,
            pr_diff=pr_diff
        )
        return await self._prompt_repository.describe_pr_user_prompt(request)