"""VCS provider implementations for multi-provider support."""

from prdiffer.infrastructure.vcs_providers.github_repository import GitHubVCSRepository
from prdiffer.infrastructure.vcs_providers.github_repository import (
    get_github_vcs_repository,
)
from prdiffer.infrastructure.vcs_providers.gitlab_repository import GitLabVCSRepository

__all__ = [
    "GitHubVCSRepository",
    "get_github_vcs_repository",
    "GitLabVCSRepository",
]
