"""Prompt use cases module for PR analysis tasks."""

from .describe_pr_user_prompt import DescribePRUserPromptUseCase
from .review_pr_user_prompt import ReviewPRUserPromptUseCase
from .update_changelog_user_prompt import UpdateChangelogUserPromptUseCase
from .describe_pr_system_prompt import DescribePRSystemPromptUseCase

__all__ = [
    'DescribePRUserPromptUseCase',
    'ReviewPRUserPromptUseCase',
    'UpdateChangelogUserPromptUseCase',
    'DescribePRSystemPromptUseCase',
]