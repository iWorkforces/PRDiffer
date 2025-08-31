from fastmcp.prompts import PromptMessage
from ccpragents.domain.entities.prompt import PromptRequest, PRDetails
from ccpragents.domain.repositories.prompt_repository import PromptRepositoryInterface


class DescribePRUseCase:
    """Use case for generating PR descriptions."""

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
        return await self._prompt_repository.describe_pr(request)


class ReviewPRUseCase:
    """Use case for reviewing PR quality and best practices."""

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self, pr_details: PRDetails, pr_commit_messages: str, pr_diff: str) -> PromptMessage:
        """Execute the PR review use case.

        Args:
            pr_details: PR identification details
            pr_commit_messages: Commit messages from the PR
            pr_diff: Diff content from the PR

        Returns:
            str: AI-generated review comments and suggestions
        """
        request = PromptRequest(
            pr_details=pr_details,
            pr_commit_messages=pr_commit_messages,
            pr_diff=pr_diff
        )
        return await self._prompt_repository.review_pr(request)


class UpdateChangelogUseCase:
    """Use case for generating changelog entries."""

    def __init__(self, prompt_repository: PromptRepositoryInterface):
        self._prompt_repository: PromptRepositoryInterface = prompt_repository

    async def execute(self, pr_url: str, pr_commit_messages: str, pr_diff: str) -> PromptMessage:
        """Execute the changelog update use case.

        Args:
            pr_url: PR URL to extract repo details from
            pr_commit_messages: Commit messages from the PR
            pr_diff: Diff content from the PR

        Returns:
            str: AI-generated changelog entries

        Raises:
            ValueError: If PR URL format is invalid
        """
        # Extract PR details from URL
        pr_details = self._extract_pr_details(pr_url)

        request = PromptRequest(
            pr_details=pr_details,
            pr_commit_messages=pr_commit_messages,
            pr_diff=pr_diff
        )
        return await self._prompt_repository.update_changelog(request)

    def _extract_pr_details(self, pr_url: str) -> PRDetails:
        """Extract PR details from GitHub PR URL.

        Args:
            pr_url: GitHub PR URL in format https://github.com/owner/repo/pull/number

        Returns:
            PRDetails: Extracted repository and PR information

        Raises:
            ValueError: If URL format is invalid
        """
        if not pr_url or not pr_url.strip():
            raise ValueError("PR URL cannot be empty")

        pr_url = pr_url.strip()

        # Basic URL validation
        if not pr_url.startswith('https://github.com/'):
            raise ValueError("PR URL must be a GitHub URL starting with https://github.com/")

        # Parse URL segments
        url_parts = pr_url.rstrip('/').replace('https://github.com/', '').split('/')

        if len(url_parts) < 3 or url_parts[2] != 'pull':
            raise ValueError("Invalid GitHub PR URL format. Expected: https://github.com/owner/repo/pull/number")

        try:
            repo_owner = url_parts[0]
            repo_name = url_parts[1]
            pr_number = int(url_parts[3]) if len(url_parts) > 3 else 0
        except (ValueError, IndexError):
            raise ValueError(f"Invalid PR URL format: {pr_url}")

        if not repo_owner or not repo_name:
            raise ValueError("Repository owner and name cannot be empty")

        if pr_number <= 0:
            raise ValueError(f"PR number must be positive, got {pr_number}")

        return PRDetails(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number
        )
