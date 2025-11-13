from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from enum import StrEnum
from datetime import datetime

from ccpragents.domain.entities.file_patch import FilePatchInfo


class PRState(StrEnum):
    """Pull request state enumeration."""

    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class PRDiff(BaseModel):
    """Domain entity representing a pull request with complete diff information.

    This entity contains comprehensive information about a pull request including
    metadata, statistics, and file changes. It serves as the aggregate root for
    PR-related operations.
    """

    # Repository and PR identification
    repo_owner: str = Field(..., description="Repository owner/organization name")
    repo_name: str = Field(..., description="Repository name")
    pr_number: int = Field(..., gt=0, description="Pull request number")

    # PR metadata
    pr_title: str = Field("", description="Pull request title")
    pr_body: str = Field("", description="Pull request description body")
    author: str = Field("", description="PR author username")
    state: PRState = Field(PRState.OPEN, description="Current PR state")
    draft: bool = Field(False, description="Whether this is a draft PR")
    mergeable: Optional[bool] = Field(None, description="Whether PR can be merged")

    # Timestamps
    created_at: str = Field("", description="PR creation timestamp (ISO format)")
    updated_at: str = Field("", description="PR last update timestamp (ISO format)")
    merged_at: Optional[str] = Field(
        None, description="PR merge timestamp (ISO format)"
    )
    closed_at: Optional[str] = Field(
        None, description="PR close timestamp (ISO format)"
    )

    # Statistics
    additions: int = Field(0, ge=0, description="Number of lines added")
    deletions: int = Field(0, ge=0, description="Number of lines deleted")
    changed_files: int = Field(0, ge=0, description="Number of files changed")

    # Commit information
    commit_sha: str = Field("", description="Latest commit SHA")

    # File changes (aggregate root for FilePatchInfo objects)
    files: List[FilePatchInfo] = Field(
        default_factory=list, description="List of file changes"
    )
    commits: List[str] = Field(
        default_factory=list, description="List of commit SHAs in PR"
    )

    # Diff content (for backward compatibility)
    diff_content: str = Field("", description="Combined diff content for all files")
    commit_messages: Optional[str] = Field(
        None, description="Formatted commit messages"
    )

    model_config = ConfigDict(
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

    @field_validator("repo_owner", "repo_name")
    def validate_repository_identifiers(cls, v):
        """Validate repository owner and name."""
        if not v or not v.strip():
            raise ValueError("Repository identifiers cannot be empty")
        if len(v.strip()) > 100:
            raise ValueError("Repository identifiers cannot exceed 100 characters")
        return v.strip()

    @field_validator("pr_title")
    def validate_pr_title(cls, v):
        """Validate PR title."""
        if v and len(v.strip()) > 500:
            raise ValueError("PR title cannot exceed 500 characters")
        return v.strip() if v else v

    def get_total_changes(self) -> int:
        """Get total number of changes (additions + deletions).

        Returns:
            int: Total number of changes
        """
        return self.additions + self.deletions

    def get_file_count_by_type(self, edit_type: str) -> int:
        """Get count of files by edit type.

        Args:
            edit_type: Type of edit (ADDED, DELETED, MODIFIED, etc.)

        Returns:
            int: Number of files with the specified edit type
        """
        return sum(1 for file in self.files if file.edit_type == edit_type)

    def has_significant_changes(self, threshold: int = 100) -> bool:
        """Check if PR has significant changes based on threshold.

        Args:
            threshold: Change threshold (default: 100 lines)

        Returns:
            bool: True if changes exceed threshold
        """
        return self.get_total_changes() > threshold

    def get_language_breakdown(self) -> dict:
        """Get breakdown of files by programming language.

        Returns:
            dict: Language -> file count mapping
        """
        language_counts = {}
        for file in self.files:
            if file.language:
                language_counts[file.language] = (
                    language_counts.get(file.language, 0) + 1
                )
        return language_counts

    def is_ready_for_review(self) -> bool:
        """Check if PR is ready for review.

        Returns:
            bool: True if PR is not a draft and has files changed
        """
        return not self.draft and self.changed_files > 0

    def get_summary(self) -> dict:
        """Get a summary of the PR.

        Returns:
            dict: PR summary with key metrics
        """
        return {
            "title": self.pr_title,
            "author": self.author,
            "state": self.state,
            "files_changed": self.changed_files,
            "additions": self.additions,
            "deletions": self.deletions,
            "total_changes": self.get_total_changes(),
            "languages": self.get_language_breakdown(),
            "ready_for_review": self.is_ready_for_review(),
        }

    def add_file(self, file_patch: "FilePatchInfo") -> None:
        """Add a file patch to the PR.

        Args:
            file_patch: FilePatchInfo to add
        """
        self.files.append(file_patch)
        self.changed_files = len(self.files)

    def remove_file(self, filename: str) -> bool:
        """Remove a file patch from the PR.

        Args:
            filename: Name of the file to remove

        Returns:
            bool: True if file was removed, False if not found
        """
        for i, file in enumerate(self.files):
            if file.filename == filename:
                self.files.pop(i)
                self.changed_files = len(self.files)
                return True
        return False

    def update_statistics(self) -> None:
        """Update statistics based on current file patches."""
        self.additions = sum(file.num_plus_lines for file in self.files)
        self.deletions = sum(file.num_minus_lines for file in self.files)
        self.changed_files = len(self.files)
