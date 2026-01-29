"""FileDiffResponse entity for structured file-level diff representation.

This module provides FileDiffResponse entity that represents individual file changes
in a pull request with structured metadata (path, status, stats, diff).
"""

from pydantic import BaseModel, Field

from prdiffer.domain.entities.file_patch import EDIT_TYPE


class FileStats(BaseModel):
    """Statistics for file changes in a PR.

    Contains line change statistics for a single file modification.
    """

    additions: int = Field(default=0, description="Number of lines added to the file")
    deletions: int = Field(
        default=0, description="Number of lines removed from the file"
    )


class FileDiffResponse(BaseModel):
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

    path: str = Field(description="File path relative to repository root")
    status: EDIT_TYPE = Field(
        description="File edit status (added, modified, deleted, renamed, unknown)"
    )
    stats: FileStats = Field(description="Line change statistics for this file")
    diff: str = Field(description="Full patch content for this file change")
