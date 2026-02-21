"""Domain use cases for the PRDiffer application."""

from .pr_diff_usecases import GetPRDiffUseCase
from prdiffer.domain.repositories import PRDiffRepositoryInterface

__all__ = [
    'PRDiffRepositoryInterface',
    'GetPRDiffUseCase',
]
