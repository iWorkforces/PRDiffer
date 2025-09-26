"""Domain use cases for the CCPRAgents application."""

from .pr_diff_usecases import GetPRDiffUseCase
from .prompt import (
    DescribePRUserPromptUseCase,
    ReviewPRUserPromptUseCase,
    UpdateChangelogUserPromptUseCase,
    DescribePRSystemPromptUseCase,
)
from ccpragents.domain.repositories import PRDiffRepositoryInterface

__all__ = [
    "PRDiffRepositoryInterface",
    "GetPRDiffUseCase",
    "DescribePRUserPromptUseCase",
    "ReviewPRUserPromptUseCase",
    "UpdateChangelogUserPromptUseCase",
    "DescribePRSystemPromptUseCase",
]
