"""GitHub PR URL parsing utility.

This module provides URL parsing functionality for GitHub pull request URLs,
supporting both 'pull/' and 'pulls/' path formats.
"""

import re
from prdiffer.domain.exceptions import InvalidURLError, InvalidPRNumberError


def parse_github_pr_url(pr_url: str) -> tuple[str, str, int]:
    """Parse a GitHub PR URL to extract owner, repository, and PR number.

    Supports both path formats:
    - https://github.com/owner/repo/pull/123
    - https://github.com/owner/repo/pulls/123

    Args:
        pr_url: The GitHub pull request URL to parse

    Returns:
        tuple[str, str, int]: (owner, repository_name, pr_number)

    Raises:
        InvalidURLError: If URL format is invalid or components are malformed
        InvalidPRNumberError: If PR number is not a valid integer
    """
    if not pr_url:
        raise InvalidURLError("PR URL cannot be None or empty")

    pr_url = pr_url.strip()

    if not pr_url:
        raise InvalidURLError("PR URL cannot be empty or whitespace-only")

    # Check URL length (prevent DoS)
    if len(pr_url) > 2000:
        raise InvalidURLError("URL too long (max 2000 characters)")

    if not pr_url.startswith("https://github.com/"):
        raise InvalidURLError(
            "URL must start with https://github.com/",
            details={"url": pr_url[:100]},
        )

    pattern = re.compile(r"^https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9._-]+)/pulls?/(\d+)/?$")

    match = pattern.match(pr_url)

    if not match:
        raise InvalidURLError(
            "Invalid GitHub PR URL format. Expected: https://github.com/owner/repo/pull/123 or https://github.com/owner/repo/pulls/123",
            details={"url": pr_url[:100]},
        )

    owner, repo_name, pr_number_str = match.groups()

    _validate_owner(owner)
    _validate_repo_name(repo_name)

    try:
        pr_number = int(pr_number_str)
    except ValueError:
        raise InvalidPRNumberError(f"Invalid PR number: {pr_number_str}")

    if pr_number <= 0:
        raise InvalidPRNumberError("PR number must be positive")

    if pr_number > 1000000:
        raise InvalidPRNumberError("PR number too large (max 1000000)")

    return owner, repo_name, pr_number


_GITLAB_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$|^[a-zA-Z0-9]$")
_GITLAB_MR_MARKER = "/-/merge_requests/"


def _validate_gitlab_path_segment(segment: str, *, kind: str) -> None:
    """Validate one GitLab namespace or project segment (no traversal / encoded separators)."""
    if not segment:
        raise InvalidURLError(f"GitLab {kind} segment cannot be empty")
    if segment in (".", ".."):
        raise InvalidURLError(f"GitLab {kind} segment cannot be a traversal token")
    if "%" in segment or "\\" in segment:
        raise InvalidURLError(f"GitLab {kind} segment cannot contain encoded or backslash separators")
    if not _GITLAB_SEGMENT_RE.fullmatch(segment):
        raise InvalidURLError(
            f"GitLab {kind} segment contains invalid characters",
            details={kind: segment},
        )
    if len(segment) > 255:
        raise InvalidURLError(f"GitLab {kind} segment too long (max 255 characters)")


def parse_gitlab_merge_request_url(pr_url: str) -> tuple[str, str, int]:
    """Parse a canonical GitLab.com merge request URL (including nested namespaces).

    Returns ``(namespace, project, iid)`` where ``namespace`` may contain
    slashes (e.g. ``group/subgroup``) and is the path before the final project
    segment. Fully anchored to ``https://gitlab.com/`` with optional trailing
    slash only — no query string or fragment.
    """
    if not pr_url:
        raise InvalidURLError("PR URL cannot be None or empty")

    pr_url = pr_url.strip()
    if not pr_url:
        raise InvalidURLError("PR URL cannot be empty or whitespace-only")
    if len(pr_url) > 2000:
        raise InvalidURLError("URL too long (max 2000 characters)")
    if not pr_url.startswith("https://gitlab.com/"):
        raise InvalidURLError(
            "URL must start with https://gitlab.com/",
            details={"url": pr_url[:100]},
        )
    if "?" in pr_url or "#" in pr_url:
        raise InvalidURLError(
            "GitLab merge request URL must not include query string or fragment",
            details={"url": pr_url[:100]},
        )

    # Optional single trailing slash only (no other trailing path noise).
    body = pr_url.removeprefix("https://gitlab.com/")
    if body.endswith("/"):
        body = body[:-1]
    if not body or body.endswith("/"):
        raise InvalidURLError(
            "Invalid GitLab merge request URL format. Expected: https://gitlab.com/group/subgroup/project/-/merge_requests/123",
            details={"url": pr_url[:100]},
        )
    if "//" in body:
        raise InvalidURLError("GitLab path cannot contain duplicate separators")

    if _GITLAB_MR_MARKER not in body:
        raise InvalidURLError(
            "Invalid GitLab merge request URL format. Expected: https://gitlab.com/group/subgroup/project/-/merge_requests/123",
            details={"url": pr_url[:100]},
        )

    project_path, iid_str = body.split(_GITLAB_MR_MARKER, 1)
    if not project_path or not iid_str or "/" in iid_str:
        raise InvalidURLError(
            "Invalid GitLab merge request URL format",
            details={"url": pr_url[:100]},
        )
    if not iid_str.isdigit():
        raise InvalidPRNumberError(f"Invalid PR number: {iid_str}")

    segments = project_path.split("/")
    if len(segments) < 2:
        raise InvalidURLError(
            "GitLab project path must include at least namespace and project",
            details={"url": pr_url[:100]},
        )

    for segment in segments:
        _validate_gitlab_path_segment(segment, kind="path")

    repo_name = segments[-1]
    owner = "/".join(segments[:-1])  # may be nested: group/subgroup

    pr_number = int(iid_str)
    if pr_number <= 0:
        raise InvalidPRNumberError("PR number must be positive")
    if pr_number > 1000000:
        raise InvalidPRNumberError("PR number too large (max 1000000)")
    return owner, repo_name, pr_number


def _validate_owner(owner: str) -> None:
    """Validate GitHub owner/organization name."""
    if not owner:
        raise InvalidURLError("Owner cannot be empty")

    if len(owner) > 39:  # GitHub's max username length
        raise InvalidURLError("Owner name too long (max 39 characters)")

    # GitHub usernames: alphanumeric, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", owner):
        raise InvalidURLError(
            "Owner contains invalid characters (allowed: a-z, A-Z, 0-9, -, _)",
            details={"owner": owner},
        )


def _validate_repo_name(repo: str) -> None:
    """Validate repository name."""
    if not repo:
        raise InvalidURLError("Repository name cannot be empty")

    if len(repo) > 100:  # GitHub's max repo name length
        raise InvalidURLError("Repository name too long (max 100 characters)")

    # GitHub repo names: alphanumeric, periods, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9._-]+$", repo):
        raise InvalidURLError(
            "Repository name contains invalid characters",
            details={"repo": repo},
        )


def validate_github_pr_url(pr_url: str) -> bool:
    """Validate if a URL is a valid GitHub PR URL.

    Supports both path formats:
    - https://github.com/owner/repo/pull/123
    - https://github.com/owner/repo/pulls/123

    Args:
        pr_url: The URL to validate

    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        parse_github_pr_url(pr_url)
        return True
    except InvalidURLError, InvalidPRNumberError:
        return False
