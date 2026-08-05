"""GitHub/GitLab PR URL parsing utilities.

Supports GitHub pull request URLs and GitLab.com / custom-hosted merge
request URLs (including nested namespaces).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

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
_GITLAB_HOST_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)"
    r"(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))+$"
    r"|localhost$"
)
_GITLAB_MR_MARKER = "/-/merge_requests/"
DEFAULT_GITLAB_BASE_URL = "https://gitlab.com"


@dataclass(frozen=True, slots=True)
class GitLabURLParts:
    """Parsed GitLab MR URL parts (GitLab.com or custom-hosted)."""

    base_url: str
    host: str
    namespace: str
    project: str
    iid: int

    @property
    def project_path(self) -> str:
        return f"{self.namespace}/{self.project}"


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


def _validate_gitlab_host(host: str) -> None:
    if not host or not _GITLAB_HOST_RE.fullmatch(host):
        raise InvalidURLError(
            "GitLab host is not a valid hostname",
            details={"host": host[:100]},
        )


def parse_gitlab_merge_request_parts(pr_url: str) -> GitLabURLParts:
    """Parse a GitLab.com or custom-hosted merge request URL.

    Accepts HTTPS MR URLs whose path ends with ``/-/merge_requests/<iid>``,
    including nested namespaces and self-managed hosts
    (e.g. ``https://gitlab.example.com/group/project/-/merge_requests/1``).
    Optional trailing slash only; no query string, fragment, or userinfo.
    """
    if not pr_url:
        raise InvalidURLError("PR URL cannot be None or empty")

    pr_url = pr_url.strip()
    if not pr_url:
        raise InvalidURLError("PR URL cannot be empty or whitespace-only")
    if len(pr_url) > 2000:
        raise InvalidURLError("URL too long (max 2000 characters)")
    if "?" in pr_url or "#" in pr_url:
        raise InvalidURLError(
            "GitLab merge request URL must not include query string or fragment",
            details={"url": pr_url[:100]},
        )

    parsed = urlparse(pr_url)
    if parsed.scheme != "https":
        raise InvalidURLError(
            "GitLab URL must use https://",
            details={"url": pr_url[:100]},
        )
    if parsed.username or parsed.password:
        raise InvalidURLError("GitLab URL must not include credentials")
    if not parsed.hostname:
        raise InvalidURLError("GitLab URL host is missing")
    if parsed.port is not None:
        # Allow non-default ports for self-managed (e.g. :8443)
        host_for_base = f"{parsed.hostname}:{parsed.port}"
    else:
        host_for_base = parsed.hostname
    _validate_gitlab_host(parsed.hostname)

    path = parsed.path or ""
    if path.endswith("/"):
        path = path[:-1]
    if not path.startswith("/") or "//" in path:
        raise InvalidURLError(
            "Invalid GitLab merge request URL path",
            details={"url": pr_url[:100]},
        )
    # path like /group/project/-/merge_requests/1
    if _GITLAB_MR_MARKER not in path:
        raise InvalidURLError(
            "Invalid GitLab merge request URL format. Expected: https://<host>/group/subgroup/project/-/merge_requests/123",
            details={"url": pr_url[:100]},
        )

    project_path, iid_str = path.split(_GITLAB_MR_MARKER, 1)
    project_path = project_path.lstrip("/")
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

    project = segments[-1]
    namespace = "/".join(segments[:-1])
    iid = int(iid_str)
    if iid <= 0:
        raise InvalidPRNumberError("PR number must be positive")
    if iid > 1000000:
        raise InvalidPRNumberError("PR number too large (max 1000000)")

    base_url = f"https://{host_for_base}"
    return GitLabURLParts(
        base_url=base_url,
        host=parsed.hostname.casefold(),
        namespace=namespace,
        project=project,
        iid=iid,
    )


def parse_gitlab_merge_request_url(pr_url: str) -> tuple[str, str, int]:
    """Parse a GitLab MR URL (GitLab.com or custom-hosted).

    Returns ``(namespace, project, iid)`` where ``namespace`` may contain
    slashes (e.g. ``group/subgroup``). For base URL / host, use
    :func:`parse_gitlab_merge_request_parts`.
    """
    parts = parse_gitlab_merge_request_parts(pr_url)
    return parts.namespace, parts.project, parts.iid


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
