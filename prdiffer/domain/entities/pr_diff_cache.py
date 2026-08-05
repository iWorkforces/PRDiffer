"""Versioned PRDiff cache entries for the GitHub full-diff v2 path."""

from __future__ import annotations

from dataclasses import dataclass

from prdiffer.domain.entities.pr_diff import PRDiff

PRDIFF_CACHE_SCHEMA_V2 = 2
GITHUB_FULL_DIFF_CACHE_PREFIX = "github-full-diff-v2"


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


def unwrap_pr_diff_cache_value(raw: object, *, key: str = "") -> PRDiff | None:
    """Accept v2 entries; ignore unversioned/v1/raw/wrong-schema values.

    When ``key`` starts with the v2 prefix, a bare PRDiff stored under that key
    is accepted (key implies schema). Wrong-type/wrong-version values return None.
    """
    if isinstance(raw, PRDiffCacheEntryV2):
        if raw.schema_version != PRDIFF_CACHE_SCHEMA_V2:
            return None
        return raw.value
    if isinstance(raw, PRDiff) and key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX):
        return raw
    return None


def wrap_pr_diff_for_cache(value: PRDiff) -> PRDiffCacheEntryV2:
    return PRDiffCacheEntryV2(schema_version=PRDIFF_CACHE_SCHEMA_V2, value=value)
