"""Synchronous python-gitlab lifecycle and immutable MR diff version selection."""

from __future__ import annotations

from typing import Any

import gitlab
import requests

from prdiffer.domain.error_codes import (
    E4001_REPO_NOT_FOUND,
    E4002_PR_NOT_FOUND,
    E5019_CONNECTION_ERROR,
    E5021_GITLAB_API_ERROR,
)
from prdiffer.domain.exceptions import (
    FullDiffIncompleteError,
    FullDiffIncompleteReason,
    GitLabAPIError,
    PRDifferException,
)
from prdiffer.infrastructure.vcs_providers.gitlab_models import (
    GitLabDiffRecord,
    GitLabDiffRefs,
    GitLabDiffSnapshot,
    GitLabVersionSummary,
)
from prdiffer.infrastructure.vcs_providers.gitlab_runtime import (
    GITLAB_COM_URL,
    GitLabNotFoundContext,
    GitLabNotFoundKind,
    map_gitlab_exception,
)

# Re-export for backward-compatible imports from gitlab_operations.
__all__ = [
    "GitLabDiffRecord",
    "GitLabDiffRefs",
    "GitLabDiffSnapshot",
    "GitLabOperations",
    "GitLabVersionSummary",
]


class GitLabOperations:
    """Execute isolated synchronous GitLab operations with fresh SDK clients.

    Strict full-diff path pins one MR diff version whose base/start/head SHAs
    exactly match the MR's current ``diff_refs``.
    """

    def __init__(
        self,
        gitlab_token: str | None = None,
        *,
        base_url: str = GITLAB_COM_URL,
    ) -> None:
        self._gitlab_token = gitlab_token
        self._base_url = (base_url or GITLAB_COM_URL).rstrip("/")

    def initialize(self, *, base_url: str | None = None) -> None:
        """Authenticate a newly created GitLab client."""
        url = (base_url or self._base_url).rstrip("/")
        try:
            with gitlab.Gitlab(url=url, private_token=self._gitlab_token) as client:
                client.auth()
        except gitlab.GitlabError, requests.RequestException:
            raise PRDifferException(
                "Failed to initialize GitLab connection",
                error_code=E5019_CONNECTION_ERROR,
            ) from None

    def get_latest_commit_sha(self, owner: str, repo: str, pr: int, *, base_url: str | None = None) -> str:
        """Return the head SHA from a pinned snapshot (compat surface)."""
        return self.select_diff_snapshot(f"{owner}/{repo}", pr, base_url=base_url).head_sha

    def get_diff_records(self, owner: str, repo: str, pr: int, *, base_url: str | None = None) -> tuple[GitLabDiffRecord, ...]:
        """Return ordered records from the pinned immutable version (compat)."""
        return self.select_diff_snapshot(f"{owner}/{repo}", pr, base_url=base_url).records

    def select_diff_snapshot(
        self,
        project_path: str,
        iid: int,
        *,
        base_url: str | None = None,
    ) -> GitLabDiffSnapshot:
        """Select and fetch exactly one MR diff version matching current diff_refs.

        ``project_path`` is the unencoded GitLab project path (e.g.
        ``group/subgroup/project``). ``base_url`` selects GitLab.com or a
        custom-hosted instance (e.g. ``https://gitlab.example.com``).
        """
        url = (base_url or self._base_url).rstrip("/")
        try:
            with gitlab.Gitlab(url=url, private_token=self._gitlab_token) as client:
                return self._select_diff_snapshot_with_client(client, project_path, iid)
        except FullDiffIncompleteError:
            raise
        except Exception as exc:
            # Prefer runtime mapper for HTTP statuses.
            not_found = GitLabNotFoundContext(GitLabNotFoundKind.MERGE_REQUEST)
            # Heuristic: project get failures often surface first
            mapped = map_gitlab_exception(exc, not_found=not_found)
            if isinstance(mapped, Exception) and mapped is not exc:
                # Refine project vs MR 404 using message when available
                if getattr(mapped, "error_code", None) is E4002_PR_NOT_FOUND:
                    status = getattr(exc, "response_code", None)
                    if status == 404 and "Project" in type(exc).__name__:
                        raise GitLabAPIError(
                            "Repository not found",
                            status_code=404,
                            error_code=E4001_REPO_NOT_FOUND,
                            details={"status_code": 404},
                        ) from None
                raise mapped from None
            if isinstance(exc, (gitlab.GitlabAuthenticationError, gitlab.GitlabGetError, gitlab.GitlabHttpError)):
                raise PRDifferException("Merge request not found", error_code=E4002_PR_NOT_FOUND) from None
            if isinstance(exc, (gitlab.GitlabConnectionError, requests.RequestException)):
                raise PRDifferException("GitLab API error", error_code=E5021_GITLAB_API_ERROR) from None
            raise

    def _select_diff_snapshot_with_client(
        self,
        client: Any,
        project_path: str,
        iid: int,
    ) -> GitLabDiffSnapshot:
        try:
            project = client.projects.get(project_path)
        except Exception as exc:
            mapped = map_gitlab_exception(
                exc,
                not_found=GitLabNotFoundContext(GitLabNotFoundKind.PROJECT),
            )
            if mapped is not exc:
                raise mapped from None
            raise

        try:
            merge_request = project.mergerequests.get(iid)
        except Exception as exc:
            mapped = map_gitlab_exception(
                exc,
                not_found=GitLabNotFoundContext(GitLabNotFoundKind.MERGE_REQUEST),
            )
            if mapped is not exc:
                raise mapped from None
            raise

        try:
            refs = GitLabDiffRefs.from_mapping(getattr(merge_request, "diff_refs", None))
        except ValueError as exc:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message=f"MR diff_refs incomplete or malformed: {exc}",
            ) from None

        try:
            version_list = list(merge_request.diffs.list(get_all=True))
        except Exception as exc:
            mapped = map_gitlab_exception(
                exc,
                not_found=GitLabNotFoundContext(GitLabNotFoundKind.MERGE_REQUEST),
            )
            if mapped is not exc:
                raise mapped from None
            raise

        matches: list[GitLabVersionSummary] = []
        for item in version_list:
            try:
                summary = GitLabVersionSummary.from_object(item)
            except ValueError:
                # Skip unparsable list entries; selection still requires exact match
                continue
            if summary.matches_refs(refs):
                matches.append(summary)

        if len(matches) != 1:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message=(f"Expected exactly one MR diff version matching diff_refs; found {len(matches)}"),
                observed=len(matches),
                limit=1,
            )

        selected = matches[0]
        try:
            version = merge_request.diffs.get(selected.version_id)
        except Exception as exc:
            mapped = map_gitlab_exception(
                exc,
                not_found=GitLabNotFoundContext(GitLabNotFoundKind.MERGE_REQUEST),
            )
            if mapped is not exc:
                raise mapped from None
            raise

        fetched = GitLabVersionSummary.from_object(version)
        if fetched.version_id != selected.version_id or not fetched.matches_refs(refs):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message="Fetched MR diff version id/refs drifted from selection",
            )

        state = str(getattr(version, "state", "") or "")
        real_size_raw = getattr(version, "real_size", None)
        real_size: int | None
        if real_size_raw is None or real_size_raw == "":
            real_size = None
        else:
            try:
                real_size = int(real_size_raw)
            except TypeError, ValueError:
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                    message="MR diff version real_size is malformed",
                ) from None

        raw_diffs = getattr(version, "diffs", None)
        if raw_diffs is None:
            raw_diffs = []
        if not isinstance(raw_diffs, list):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message="MR diff version diffs payload is malformed",
            )

        records: list[GitLabDiffRecord] = []
        for item in raw_diffs:
            try:
                records.append(GitLabDiffRecord.from_mapping(item if isinstance(item, dict) else _as_dict(item)))
            except ValueError as exc:
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                    message=f"Malformed embedded diff record: {exc}",
                ) from None

        return GitLabDiffSnapshot(
            project_path=project_path,
            iid=iid,
            version_id=selected.version_id,
            base_sha=refs.base_sha,
            start_sha=refs.start_sha,
            head_sha=refs.head_sha,
            state=state,
            real_size=real_size,
            records=tuple(records),
        )


def _as_dict(raw: object) -> dict[str, Any]:
    as_dict = getattr(raw, "asdict", None)
    if callable(as_dict):
        data = as_dict()
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items()}
    attributes = getattr(raw, "attributes", None)
    if isinstance(attributes, dict):
        return {str(k): v for k, v in attributes.items()}
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    raise ValueError("cannot coerce diff record")
