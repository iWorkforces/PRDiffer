"""Domain entities for the PRDiffer application."""

from .file_patch import FilePatchInfo, EDIT_TYPE
from .pr_diff import PRDiff

__all__ = [
    "FilePatchInfo",
    "EDIT_TYPE",
    "PRDiff",
]
