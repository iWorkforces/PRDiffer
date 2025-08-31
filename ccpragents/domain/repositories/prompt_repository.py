"""Repository interface for prompt processing operations."""
from abc import ABC, abstractmethod

from ccpragents.domain.entities.prompt import PromptRequest


class PromptRepositoryInterface(ABC):
    """Abstract interface for prompt repository operations.

    This interface defines the contract for AI-powered prompt processing,
    following Clean Architecture principles.
    """

    @abstractmethod
    async def describe_pr_user_prompt(self, request: PromptRequest) -> str:
        """Generate a description of pull request changes.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: AI-generated description of the PR changes
        """
        pass

    @abstractmethod
    async def review_pr_user_prompt(self, request: PromptRequest) -> str:
        """Review a pull request for quality and best practices.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: AI-generated review comments and suggestions
        """
        pass

    @abstractmethod
    async def update_changelog_user_prompt(self, request: PromptRequest) -> str:
        """Generate changelog entries for a pull request.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: AI-generated changelog entries
        """
        pass

    @abstractmethod
    async def describe_pr_system_prompt(self) -> str:
        """Generate a system prompt for PR description tasks.

        Returns:
            str: System prompt for PR description
        """
        pass
