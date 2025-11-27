from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class PRDiff(BaseModel):
    """Domain entity representing a pull request with diff content and commit messages.

    This entity contains the essential diff content and commit messages
    for PR analysis, along with statistics and metadata for API enhancement.
    """

    # Core content (existing fields)
    diff_content: str = Field(
        default="", description="Combined diff content for all files"
    )
    commit_messages: Optional[str] = Field(
        default=None, description="Formatted commit messages"
    )

    # Phase 3: Statistics for API enhancement
    files_changed: int = Field(
        default=0, description="Number of files changed in the PR"
    )
    total_additions: int = Field(
        default=0, description="Total lines added across all files"
    )
    total_deletions: int = Field(
        default=0, description="Total lines deleted across all files"
    )

    # Phase 3: Generation metadata
    generation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata about diff generation (timing, cache status, etc.)",
    )

    # Phase 3: File-level statistics
    file_summaries: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Summary statistics for each file in the PR"
    )

    @property
    def total_changes(self) -> int:
        """Get total number of line changes (additions + deletions).

        Returns:
            int: Total changes across all files
        """
        return self.total_additions + self.total_deletions

    @property
    def has_content(self) -> bool:
        """Check if the PR diff has any content.

        Returns:
            bool: True if there is diff content
        """
        return bool(self.diff_content and self.diff_content.strip())

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the PR diff.

        Returns:
            Dict[str, Any]: Statistics including file counts, line changes, etc.
        """
        return {
            "files_changed": self.files_changed,
            "total_additions": self.total_additions,
            "total_deletions": self.total_deletions,
            "total_changes": self.total_changes,
            "has_content": self.has_content,
            "commit_count": len(self.commit_messages.split("\n"))
            if self.commit_messages
            else 0,
        }

    def get_response_envelope(self) -> Dict[str, Any]:
        """Get a complete response envelope with all data and metadata.

        This method provides a standardized response format for API clients
        that includes content, statistics, and generation metadata.

        Returns:
            Dict[str, Any]: Complete response envelope
        """
        return {
            "content": {
                "diff": self.diff_content,
                "commit_messages": self.commit_messages,
            },
            "statistics": self.get_statistics(),
            "metadata": self.generation_metadata or {},
            "file_summaries": self.file_summaries or [],
        }
