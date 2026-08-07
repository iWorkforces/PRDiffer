"""Versioned PRDiff cache entries and provider-neutral strict session identity."""

from __future__ import annotations

from dataclasses import dataclass

from prdiffer.domain.entities.pr_diff import PRDiff

PRDIFF_CACHE_SCHEMA_V1 = 1
PRDIFF_CACHE_SCHEMA_V2 = 2
# Legacy GitHub key prefix (ignored on read; never migrated).
GITHUB_FULL_DIFF_CACHE_PREFIX_V2 = "github-full-diff-v2"
GITHUB_FULL_DIFF_CACHE_PREFIX = GITHUB_FULL_DIFF_CACHE_PREFIX_V2  # back-compat alias
# Active GitHub strict identity (merge-base + head). Value schema remains V2.
GITHUB_FULL_DIFF_CACHE_PREFIX_V3 = "github-full-diff-v3"
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
    """Legacy GitHub PRDiff cache key (v2; head-only). Kept for rejection tests."""
    return f"{GITHUB_FULL_DIFF_CACHE_PREFIX_V2}:{owner.casefold()}:{repo.casefold()}:{pr_number}:{head_sha}"


def github_full_diff_v2_identity(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
) -> StrictPRDiffCacheIdentity:
    """Legacy GitHub full-diff v2 identity (not used by active sessions)."""
    return StrictPRDiffCacheIdentity(
        cache_key=github_full_diff_v2_key(owner, repo, pr_number, head_sha),
        validation_token=head_sha,
        schema_version=PRDIFF_CACHE_SCHEMA_V2,
    )


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


def _is_active_github_strict_key(key: str) -> bool:
    return key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3)


def _is_legacy_github_v2_key(key: str) -> bool:
    return key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V2)


def _key_matches_identity(key: str, identity: StrictPRDiffCacheIdentity) -> bool:
    if not key:
        return True
    return key == identity.cache_key or key.endswith(identity.cache_key)


def unwrap_pr_diff_cache_value(
    raw: object,
    *,
    key: str = "",
    identity: StrictPRDiffCacheIdentity | None = None,
) -> PRDiff | None:
    """Accept strict bare PRDiff under GitHub-v3 or GitLab-v1 key prefixes.

    GitHub v2 keys are never migrated: bare or wrapped values under a v2 key
    miss when the active identity is v3. ``PRDiffCacheEntryV2`` remains the
    value schema for successful strict writes under active keys.
    """
    if isinstance(raw, PRDiffCacheEntryV2):
        if raw.schema_version != PRDIFF_CACHE_SCHEMA_V2:
            return None
        if identity is not None:
            if identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V2):
                # Legacy v2 identity is never an active session hit.
                return None
            if not _key_matches_identity(key, identity):
                return None
            if identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3):
                if key and _is_legacy_github_v2_key(key):
                    return None
                if key and not (_is_active_github_strict_key(key) or key == identity.cache_key or key.endswith(identity.cache_key)):
                    return None
        elif key and _is_legacy_github_v2_key(key):
            # Wrapped values under legacy v2 keys are ignored (no migration).
            return None
        return raw.value
    if not isinstance(raw, PRDiff):
        return None
    if identity is not None:
        if not _key_matches_identity(key, identity):
            return None
        if identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3):
            if key and _is_legacy_github_v2_key(key):
                return None
            return raw if (not key) or _is_active_github_strict_key(key) or key == identity.cache_key or key.endswith(identity.cache_key) else None
        if identity.cache_key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V2):
            return None
        if identity.cache_key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX):
            return raw if (not key) or key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX) or key == identity.cache_key else None
        return None
    if _is_active_github_strict_key(key) or key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX):
        return raw
    # Bare PRDiff under legacy GitHub v2 or unversioned keys is ignored.
    return None


def wrap_pr_diff_for_cache(value: PRDiff) -> PRDiffCacheEntryV2:
    return PRDiffCacheEntryV2(schema_version=PRDIFF_CACHE_SCHEMA_V2, value=value)
