"""Versioned PRDiff cache entries and provider-neutral strict session identity."""

from __future__ import annotations

from dataclasses import dataclass

from prdiffer.domain.entities.pr_diff import PRDiff

PRDIFF_CACHE_SCHEMA_V1 = 1
PRDIFF_CACHE_SCHEMA_V2 = 2
GITHUB_FULL_DIFF_CACHE_PREFIX = "github-full-diff-v2"
GITLAB_FULL_DIFF_CACHE_PREFIX = "gitlab-full-diff-v1"


@dataclass(frozen=True)
class StrictPRDiffCacheIdentity:
    """Provider-neutral cache key + validation token for a strict session."""

    cache_key: str
    validation_token: str
    schema_version: int


@dataclass(frozen=True)
class PRDiffCacheEntryV2:
    """Strict full-diff cache value (schema version 2 only)."""

    schema_version: int
    value: PRDiff

    def __post_init__(self) -> None:
        if self.schema_version != PRDIFF_CACHE_SCHEMA_V2:
            raise ValueError(f"Unsupported PRDiff cache schema_version: {self.schema_version}")


def github_full_diff_v2_key(owner: str, repo: str, pr_number: int, head_sha: str) -> str:
    """Exact GitHub PRDiff cache key for the session/v2 path."""
    return f"{GITHUB_FULL_DIFF_CACHE_PREFIX}:{owner.casefold()}:{repo.casefold()}:{pr_number}:{head_sha}"


def github_full_diff_v2_identity(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
) -> StrictPRDiffCacheIdentity:
    """Strict session identity for GitHub full-diff v2 (key + head SHA token)."""
    return StrictPRDiffCacheIdentity(
        cache_key=github_full_diff_v2_key(owner, repo, pr_number, head_sha),
        validation_token=head_sha,
        schema_version=PRDIFF_CACHE_SCHEMA_V2,
    )


def gitlab_full_diff_v1_key(
    namespace: str,
    repo: str,
    iid: int,
    version_id: int | str,
    base_sha: str,
    start_sha: str,
    head_sha: str,
) -> str:
    """Exact GitLab strict full-diff v1 cache key (no ``gitlab:`` prefix)."""
    return f"{GITLAB_FULL_DIFF_CACHE_PREFIX}:{namespace.casefold()}:{repo.casefold()}:{iid}:{version_id}:{base_sha}:{start_sha}:{head_sha}"


def gitlab_full_diff_v1_validation_token(
    version_id: int | str,
    base_sha: str,
    start_sha: str,
    head_sha: str,
) -> str:
    """Validation token: version ID plus base/start/head SHAs."""
    return f"{version_id}:{base_sha}:{start_sha}:{head_sha}"


def gitlab_full_diff_v1_identity(
    namespace: str,
    repo: str,
    iid: int,
    version_id: int | str,
    base_sha: str,
    start_sha: str,
    head_sha: str,
) -> StrictPRDiffCacheIdentity:
    """Strict session identity for GitLab full-diff v1."""
    return StrictPRDiffCacheIdentity(
        cache_key=gitlab_full_diff_v1_key(namespace, repo, iid, version_id, base_sha, start_sha, head_sha),
        validation_token=gitlab_full_diff_v1_validation_token(version_id, base_sha, start_sha, head_sha),
        schema_version=PRDIFF_CACHE_SCHEMA_V1,
    )


def unwrap_pr_diff_cache_value(
    raw: object,
    *,
    key: str = "",
    identity: StrictPRDiffCacheIdentity | None = None,
) -> PRDiff | None:
    """Accept strict bare PRDiff under GitHub-v2 or GitLab-v1 key prefixes.

    When ``identity`` is provided, the key must match ``identity.cache_key``
    (or start with a known strict prefix). Legacy/unversioned/wrong values return None.
    """
    if isinstance(raw, PRDiffCacheEntryV2):
        if raw.schema_version != PRDIFF_CACHE_SCHEMA_V2:
            return None
        return raw.value
    if not isinstance(raw, PRDiff):
        return None
    if identity is not None:
        if key and key != identity.cache_key and not key.endswith(identity.cache_key):
            # Allow only exact identity key for strict path (no namespace prepend on session path).
            return None
        if identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX):
            return raw if key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX) or key == identity.cache_key else None
        if identity.cache_key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX):
            return raw if key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX) or key == identity.cache_key else None
        return None
    if key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX) or key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX):
        return raw
    return None


def wrap_pr_diff_for_cache(value: PRDiff) -> PRDiffCacheEntryV2:
    return PRDiffCacheEntryV2(schema_version=PRDIFF_CACHE_SCHEMA_V2, value=value)
