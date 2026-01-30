"""Mappers for converting PyGithub objects to domain entities.

This module contains mapping functions that convert PyGithub library objects
to our pure domain entities. This maintains Clean Architecture by keeping
PyGithub dependencies in the infrastructure layer only.
"""

from typing import Optional
from github.Repository import Repository as PyGithubRepository
from github.PullRequest import PullRequest as PyGithubPullRequest
from prdiffer.domain.entities import Repository, PullRequest, PRState


def map_pygithub_repository_to_domain(
    gh_repo: PyGithubRepository,
) -> Repository:
    """Convert PyGithub Repository to domain Repository entity.

    Args:
        gh_repo: PyGithub Repository object

    Returns:
        Repository: Domain entity with mapped fields
    """
    return Repository(
        name=gh_repo.name,
        owner=gh_repo.owner.login,
        full_name=gh_repo.full_name,
        default_branch=gh_repo.default_branch,
        description=gh_repo.description,
        is_private=gh_repo.private,
        clone_url=gh_repo.clone_url,
        html_url=gh_repo.html_url,
    )


def map_pygithub_pr_to_domain(
    gh_pr: PyGithubPullRequest,
) -> PullRequest:
    """Convert PyGithub PullRequest to domain PullRequest entity.

    Args:
        gh_pr: PyGithub PullRequest object

    Returns:
        PullRequest: Domain entity with mapped fields
    """
    # Determine PR state (OPEN, CLOSED, or MERGED)
    if gh_pr.merged:
        state = PRState.MERGED
    elif gh_pr.state == "closed":
        state = PRState.CLOSED
    else:
        state = PRState.OPEN

    # Extract author username (handle None case)
    author: Optional[str] = None
    if gh_pr.user:
        author = gh_pr.user.login

    # Format timestamps as ISO 8601 strings (handle None case)
    created_at: Optional[str] = None
    if gh_pr.created_at:
        created_at = gh_pr.created_at.isoformat()

    updated_at: Optional[str] = None
    if gh_pr.updated_at:
        updated_at = gh_pr.updated_at.isoformat()

    merged_at: Optional[str] = None
    if gh_pr.merged_at:
        merged_at = gh_pr.merged_at.isoformat()

    return PullRequest(
        number=gh_pr.number,
        title=gh_pr.title,
        state=state,
        head_sha=gh_pr.head.sha,
        base_sha=gh_pr.base.sha,
        head_ref=gh_pr.head.ref,
        base_ref=gh_pr.base.ref,
        author=author,
        body=gh_pr.body,
        created_at=created_at,
        updated_at=updated_at,
        merged_at=merged_at,
        html_url=gh_pr.html_url,
    )
