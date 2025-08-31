"""Domain repository interfaces for the CCPRAgents application."""

from .pr_diff_repository import PRDiffRepositoryInterface
from.prompt_repository import PromptRepositoryInterface

__all__ = [
    "PRDiffRepositoryInterface",
    "PromptRepositoryInterface"
]