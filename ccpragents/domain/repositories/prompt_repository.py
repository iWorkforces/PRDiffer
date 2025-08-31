'''Repository interface for prompt processing operations.'''
from abc import ABC, abstractmethod

from ccpragents.domain.entities.prompt import PromptRequest


class PromptRepositoryInterface(ABC):
    '''Abstract interface for prompt repository operations.

    This interface defines the contract for AI-powered prompt processing,
    following Clean Architecture principles.
    '''

    @abstractmethod
    async def describe_pr_user_prompt(self, request: PromptRequest) -> str:
        '''Generate a description of pull request changes.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: AI-generated description of the PR changes
        '''
        pass

    @abstractmethod
    async def review_pr_user_prompt(self, request: PromptRequest) -> str:
        '''Review a pull request for quality and best practices.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: AI-generated review comments and suggestions
        '''
        pass

    @abstractmethod
    async def update_changelog_user_prompt(self, request: PromptRequest) -> str:
        '''Generate changelog entries for a pull request.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: AI-generated changelog entries
        '''
        pass

    @abstractmethod
    async def describe_pr_system_prompt(self) -> str:
        '''Generate a system prompt for PR description tasks.

        Returns:
            str: System prompt for PR description
        '''
        pass

    @abstractmethod
    async def review_pr_system_prompt(self) -> str:
        '''Generate a system prompt for PR review tasks.

        Returns:
            str: System prompt for PR code review
        '''
        pass

    @abstractmethod
    async def update_changelog_system_prompt(self) -> str:
        '''Generate a system prompt for changelog generation tasks.

        Returns:
            str: System prompt for changelog updates
        '''
        pass

    @abstractmethod
    async def approve_pr_user_prompt(self, request: PromptRequest) -> str:
        '''Generate a prompt for PR approval decisions.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for PR approval decision making
        '''
        pass

    @abstractmethod
    async def approve_pr_system_prompt(self) -> str:
        '''Generate a system prompt for PR approval tasks.

        Returns:
            str: System prompt for PR approval
        '''
        pass
