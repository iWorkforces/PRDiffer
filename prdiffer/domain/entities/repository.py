"""Domain entity for VCS Repository (pure, no external dependencies)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Repository:
    """Domain representation of a VCS repository.

    This is a pure domain entity with no dependencies on external VCS libraries
    like PyGithub. It represents the essential repository information needed
    for domain logic.
    """

    name: str
    """Repository name only (e.g., 'myrepo')"""

    owner: str
    """Owner/organization name (e.g., 'acme')"""

    full_name: str
    """Full repository name in 'owner/repo' format"""

    default_branch: str
    """Default branch name (e.g., 'main', 'master')"""

    description: Optional[str] = None
    """Repository description"""

    is_private: bool = False
    """Whether the repository is private"""

    clone_url: Optional[str] = None
    """URL for cloning the repository"""

    html_url: Optional[str] = None
    """Web URL for the repository"""
