"""Domain use cases for the CCPRAgents application."""

from .pr_diff_usecases import GetPRDiffUseCase, GetPRDiffUseCaseLegacy
from ccpragents.domain.repositories import PRDiffRepositoryInterface

__all__ = [
    "PRDiffRepositoryInterface",
    "GetPRDiffUseCase",
    "GetPRDiffUseCaseLegacy",
]
