"""Prompt repository implementation."""
from typing import Optional
from ccpragents.domain.entities.prompt import PRDetails, PromptRequest
from ccpragents.domain.repositories.prompt_repository import PromptRepositoryInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class PromptRepository(PromptRepositoryInterface):
    """Repository for prompt processing.

    This repository provides prompt generation for PR analysis tasks.
    """

    def __init__(self):
        """Initialize the prompt repository."""
        self._logger = get_logger()
        self._logger.info("Initializing PromptRepository", component="prompt_repository")

    async def describe_pr(self, request: PromptRequest) -> str:
        """Generate a description prompt for pull request changes.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for describing PR changes
        """
        # Generate prompt in XML format
        prompt = f"""<prompt type="describe_pr">
  <instruction>Describe the changes in this pull request:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <requirements>
    <requirement>Focus on what the PR does overall</requirement>
    <requirement>Highlight key changes made</requirement>
    <requirement>Explain what problems it solves</requirement>
    <requirement>Note any notable improvements or breaking changes</requirement>
    <requirement>Be specific and actionable</requirement>
    <requirement>Avoid generic descriptions</requirement>
  </requirements>
</prompt>"""

        self._logger.info("Generated PR description prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt

    async def review_pr(self, request: PromptRequest) -> str:
        """Generate a review prompt for code quality and best practices.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for reviewing PR quality
        """
        # Generate prompt in XML format
        prompt = f"""<prompt type="review_pr">
  <instruction>Review this pull request for code quality and best practices:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <review_categories>
    <category>Code quality and best practices</category>
    <category>Potential bugs or issues</category>
    <category>Security concerns</category>
    <category>Performance implications</category>
    <category>Maintainability and readability</category>
    <category>Test coverage considerations</category>
    <category>Documentation needs</category>
  </review_categories>
  <requirements>
    <requirement>Provide specific, actionable feedback</requirement>
    <requirement>Structure review with clear sections</requirement>
    <requirement>Prioritize most important issues first</requirement>
    <requirement>Be constructive and provide specific suggestions</requirement>
  </requirements>
</prompt>"""

        self._logger.info("Generated PR review prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt

    async def update_changelog(self, request: PromptRequest) -> str:
        """Generate a changelog prompt for a pull request.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for generating changelog entries
        """
        # Generate prompt in XML format
        prompt = f"""<prompt type="update_changelog">
  <instruction>Generate changelog entries for this pull request:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <changelog_categories>
    <category type="breaking">Breaking changes (marked with BREAKING CHANGE:)</category>
    <category type="feature">New features (Added:)</category>
    <category type="bug">Bug fixes (Fixed:)</category>
    <category type="performance">Performance improvements (Performance:)</category>
    <category type="docs">Documentation updates (Docs:)</category>
    <category type="dependencies">Dependency updates (Dependencies:)</category>
  </changelog_categories>
  <requirements>
    <requirement>Follow standard changelog conventions</requirement>
    <requirement>Keep entries concise but informative</requirement>
    <requirement>Group related changes when appropriate</requirement>
  </requirements>
</prompt>"""

        self._logger.info("Generated changelog prompt",
                        component="prompt_repository",
                        pr_details=str(request.pr_details))
        return prompt


# Global instance for singleton pattern
_prompt_repository: Optional[PromptRepository] = None


def get_prompt_repository() -> PromptRepository:
    """Get the global prompt repository instance (singleton pattern).

    Returns:
        PromptRepository: The global prompt repository instance
    """
    global _prompt_repository
    if _prompt_repository is None:
        _prompt_repository = PromptRepository()
    return _prompt_repository
