"""Versioned PRDiff cache entries and provider-neutral strict session identity."""

from __future__ import annotations

from dataclasses import dataclass

from prdiffer.domain.entities.pr_diff import PRDiff

PRDIFF_CACHE_SCHEMA_V1 = 1
PRDIFF_CACHE_SCHEMA_V2 = 2
# GitHub strict identity prefix (merge-base + head). Value schema remains V2.
GITHUB_FULL_DIFF_CACHE_PREFIX = "github-full-diff-v3"
GITHUB_FULL_DIFF_CACHE_PREFIX_V3 = GITHUB_FULL_DIFF_CACHE_PREFIX
GITLAB_FULL_DIFF_CACHE_PREFIX = "gitlab-full-diff-v1"


@dataclass(frozen=True)
class StrictPRDiffCacheIdentity:
    """Provider-neutral cache key + validation token for a strict session."""

    cache_key: str
    validation_token: str
    schema_version: int


@dataclass(frozen=True)
class PRDiffCacheEntryV2:
    """Strict full-diff cache *value* wrapper (schema version 2 only).

    Name refers to the value serialization schema, not the GitHub key prefix.
    """

    schema_version: int
    value: PRDiff

    def __post_init__(self) -> None:
        if self.schema_version != PRDIFF_CACHE_SCHEMA_V2:
            raise ValueError(f"Unsupported PRDiff cache schema_version: {self.schema_version}")


def github_full_diff_v3_key(
    owner: str,
    repo: str,
    pr_number: int,
    merge_base_sha: str,
    head_sha: str,
) -> str:
    """Exact GitHub PRDiff cache key for the session/v3 merge-base path."""
    return f"{GITHUB_FULL_DIFF_CACHE_PREFIX_V3}:{owner.casefold()}:{repo.casefold()}:{pr_number}:{merge_base_sha}:{head_sha}"


def github_full_diff_v3_validation_token(merge_base_sha: str, head_sha: str) -> str:
    """Validation token binds the same immutable merge-base and head refs as the key."""
    return f"{merge_base_sha}:{head_sha}"


def github_full_diff_v3_identity(
    owner: str,
    repo: str,
    pr_number: int,
    merge_base_sha: str,
    head_sha: str,
) -> StrictPRDiffCacheIdentity:
    """Strict session identity for GitHub full-diff v3 (merge-base + head).

    Cached *value* schema remains ``PRDiffCacheEntryV2`` / ``PRDIFF_CACHE_SCHEMA_V2``.
    """
    return StrictPRDiffCacheIdentity(
        cache_key=github_full_diff_v3_key(owner, repo, pr_number, merge_base_sha, head_sha),
        validation_token=github_full_diff_v3_validation_token(merge_base_sha, head_sha),
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
    *,
    host: str = "gitlab.com",
) -> str:
    """Exact GitLab strict full-diff v1 cache key (includes host for multi-instance).

    Format: ``gitlab-full-diff-v1:{host}:{ns}:{repo}:{iid}:{ver}:{base}:{start}:{head}``
    """
    return f"{GITLAB_FULL_DIFF_CACHE_PREFIX}:{host.casefold()}:{namespace.casefold()}:{repo.casefold()}:{iid}:{version_id}:{base_sha}:{start_sha}:{head_sha}"


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
    *,
    host: str = "gitlab.com",
) -> StrictPRDiffCacheIdentity:
    """Strict session identity for GitLab full-diff v1 (host-aware)."""
    return StrictPRDiffCacheIdentity(
        cache_key=gitlab_full_diff_v1_key(namespace, repo, iid, version_id, base_sha, start_sha, head_sha, host=host),
        validation_token=gitlab_full_diff_v1_validation_token(version_id, base_sha, start_sha, head_sha),
        schema_version=PRDIFF_CACHE_SCHEMA_V1,
    )


def _is_github_strict_key(key: str) -> bool:
    return key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3)


def _key_matches_identity(key: str, identity: StrictPRDiffCacheIdentity) -> bool:
    """Exact key match only (no empty-key pass-through, no endswith)."""
    if not key:
        return False
    return key == identity.cache_key


def unwrap_pr_diff_cache_value(
    raw: object,
    *,
    key: str = "",
    identity: StrictPRDiffCacheIdentity | None = None,
) -> PRDiff | None:
    """Accept strict bare PRDiff under GitHub-v3 or GitLab-v1 key prefixes.

    Unknown or non-strict keys miss. ``PRDiffCacheEntryV2`` is the value schema
    for successful writes under active keys (not a key-prefix version).
    """
    if isinstance(raw, PRDiffCacheEntryV2):
        if raw.schema_version != PRDIFF_CACHE_SCHEMA_V2:
            return None
        if identity is not None and not _key_matches_identity(key, identity):
            return None
        if identity is not None and identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3):
            if key and not (_is_github_strict_key(key) or key == identity.cache_key or key.endswith(identity.cache_key)):
                return None
        return raw.value
    if not isinstance(raw, PRDiff):
        return None
    if identity is not None:
        if not _key_matches_identity(key, identity):
            return None
        if identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3):
            return raw if (not key) or _is_github_strict_key(key) or key == identity.cache_key or key.endswith(identity.cache_key) else None
        if identity.cache_key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX):
            return raw if (not key) or key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX) or key == identity.cache_key else None
        return None
    if _is_github_strict_key(key) or key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX):
        return raw
    return None


def wrap_pr_diff_for_cache(value: PRDiff) -> PRDiffCacheEntryV2:
    return PRDiffCacheEntryV2(schema_version=PRDIFF_CACHE_SCHEMA_V2, value=value)
