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
    - patch → diff (generated full-context string on the public surface)
    - old_filename → previous_path (renames only)
    """

    path: str
    status: EDIT_TYPE
    stats: FileStats
    diff: str
    previous_path: str | None = None

    def __post_init__(self) -> None:
        """Enforce rename metadata invariant without a completeness flag."""
        if self.previous_path is None:
            return
        if self.status != EDIT_TYPE.RENAMED:
            raise ValueError(
                "previous_path is only valid when status is RENAMED "
                f"(got status={self.status!s}, previous_path={self.previous_path!r})"
            )
        if self.previous_path == self.path:
            raise ValueError("previous_path must differ from path for renames")
