"""Domain entities for the CCPRAgents application."""

from .file_patch import FilePatchInfo, EDIT_TYPE
from .pr_diff import PRDiff, PRState

__all__ = [
    "FilePatchInfo",
    "EDIT_TYPE",
    "PRDiff",
    "PRState",
]
