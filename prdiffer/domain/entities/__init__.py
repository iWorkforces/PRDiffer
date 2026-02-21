"""Domain entities for the PRDiffer application."""

from .file_patch import FilePatchInfo, EDIT_TYPE
from .pr_diff import PRDiff
from .repository import Repository
from .pull_request import PullRequest, PRState

__all__ = [
    "FilePatchInfo",
    "EDIT_TYPE",
    "PRDiff",
    "Repository",
    "PullRequest",
    "PRState",
]
