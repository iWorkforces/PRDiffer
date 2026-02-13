"""FileDiffResponse entity for structured file-level diff representation.

This module provides FileDiffResponse entity that represents individual file changes
in a pull request with structured metadata (path, status, stats, diff).
"""

from dataclasses import dataclass

from prdiffer.domain.entities.file_patch import EDIT_TYPE


@dataclass(frozen=True)
class FileStats:
    """Statistics for file changes in a PR.

    Contains line change statistics for a single file modification.
    """

    additions: int = 0
    deletions: int = 0


@dataclass(frozen=True)
class FileDiffResponse:
    """Domain entity representing a file change in a pull request.

    This entity contains structured information about a single file change,
    including file path, edit status, statistics, and full diff content.
    Used for MCP tool response to provide file-level detail instead of
    concatenated string format.

    Field mapping from FilePatchInfo:
    - filename → path
    - edit_type → status
    - num_plus_lines → stats.additions
    - num_minus_lines → stats.deletions
    - patch → diff
    """

    path: str
    status: EDIT_TYPE
    stats: FileStats
    diff: str
