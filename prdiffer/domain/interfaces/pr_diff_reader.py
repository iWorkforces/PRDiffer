"""Session-capable PR diff reader contracts (strict full-diff path).

Non-session readers keep the legacy PRDiffReader protocol
in ``domain.usecases.pr_diff_usecases``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import StrictPRDiffCacheIdentity
from prdiffer.domain.usecases.pr_diff_usecases import PRDiffReader


@dataclass(frozen=True)
class PRDiffSnapshot:
    """Immutable PR metadata captured once per request session."""

    owner: str
    repo: str
    pr_number: int
    base_sha: str
    head_sha: str
    authoritative_changed_files: int


class PRDiffReadSessionInterface(Protocol):
    """Request-local session for inventory/content against one PR snapshot."""

    @property
    def snapshot(self) -> PRDiffSnapshot:
        """Immutable metadata for this open session."""
        ...

    @property
    def cache_identity(self) -> StrictPRDiffCacheIdentity:
        """Provider-neutral cache key + validation token for this session."""
        ...

    async def build_pr_diff(self) -> PRDiff:
        """Build a complete PRDiff using handles opened for this session."""
        ...

    async def aclose(self) -> None:
        """Release request-local resources (always called from finally)."""
        ...


@runtime_checkable
class SessionPRDiffReader(PRDiffReader, Protocol):
    """Structural capability: open a request-local PR diff session."""

    async def open_pr_diff_session(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        /,
    ) -> PRDiffReadSessionInterface:
        """Open one session (one client/repo/PR metadata lookup)."""
        ...
