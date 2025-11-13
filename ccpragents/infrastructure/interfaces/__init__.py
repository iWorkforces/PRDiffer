"""Infrastructure layer interfaces for Clean Architecture."""

from .github_file_service import GitHubFileServiceInterface
from .commit_service import CommitServiceInterface
from .diff_compilation_service import DiffCompilationServiceInterface

__all__ = [
    "GitHubFileServiceInterface",
    "CommitServiceInterface",
    "DiffCompilationServiceInterface",
]
