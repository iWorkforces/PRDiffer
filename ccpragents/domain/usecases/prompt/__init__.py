"""Prompt use cases module for PR analysis tasks."""

from .describe_pr_user_prompt import DescribePRUserPromptUseCase
from .review_pr_user_prompt import ReviewPRUserPromptUseCase
from .update_changelog_user_prompt import UpdateChangelogUserPromptUseCase
from .describe_pr_system_prompt import DescribePRSystemPromptUseCase
from .review_pr_system_prompt import ReviewPRSystemPromptUseCase
from .update_changelog_system_prompt import UpdateChangelogSystemPromptUseCase
from .approve_pr_user_prompt import ApprovePRUserPromptUseCase
from .approve_pr_system_prompt import ApprovePRSystemPromptUseCase

__all__ = [
    'DescribePRUserPromptUseCase',
    'ReviewPRUserPromptUseCase',
    'UpdateChangelogUserPromptUseCase',
    'DescribePRSystemPromptUseCase',
    'ReviewPRSystemPromptUseCase',
    'UpdateChangelogSystemPromptUseCase',
    'ApprovePRUserPromptUseCase',
    'ApprovePRSystemPromptUseCase',
]