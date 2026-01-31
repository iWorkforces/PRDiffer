"""Domain entity for VCS Pull Request (pure, no external dependencies)."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class PRState(StrEnum):
    """Pull request state enumeration."""

    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


@dataclass
class PullRequest:
    """Domain representation of a VCS pull request.

    This is a pure domain entity with no dependencies on external VCS libraries
    like PyGithub. It represents the essential pull request information needed
    for domain logic.
    """

    number: int
    """Pull request number"""

    title: str
    """Pull request title"""

    state: PRState
    """Current state of the pull request"""

    head_sha: str
    """Commit SHA of the PR head (source branch)"""

    base_sha: str
    """Commit SHA of the PR base (target branch)"""

    head_ref: str
    """Branch name for the head (source)"""

    base_ref: str
    """Branch name for the base (target)"""

    author: Optional[str] = None
    """Pull request author username"""

    body: Optional[str] = None
    """Pull request description/body"""

    created_at: Optional[str] = None
    """ISO 8601 timestamp when PR was created"""

    updated_at: Optional[str] = None
    """ISO 8601 timestamp when PR was last updated"""

    merged_at: Optional[str] = None
    """ISO 8601 timestamp when PR was merged (if applicable)"""

    html_url: Optional[str] = None
    """Web URL for the pull request"""
