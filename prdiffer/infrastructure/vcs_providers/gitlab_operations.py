"""Synchronous python-gitlab lifecycle and immutable MR diff version selection."""

from __future__ import annotations

from typing import TypeGuard

import gitlab
import requests

from prdiffer.domain.error_codes import (
    E5019_CONNECTION_ERROR,
)
from prdiffer.domain.exceptions import (
    FullDiffIncompleteError,
    FullDiffIncompleteReason,
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
    """Execute isolated synchronous GitLab operations with a provided SDK client.

    Strict full-diff path pins one MR diff version whose base/start/head SHAs
    exactly match the MR's current ``diff_refs``.

    Production callers must obtain the client via :class:`GitLabRuntime`
    (capacity, deadline, host allowlist). Synchronous helpers that open their
    own clients exist only for isolated unit tests and initialization probes.
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
        """Authenticate a newly created GitLab client (blocking probe)."""
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

        Prefer :meth:`select_with_client` under :meth:`GitLabRuntime.run_blocking`
        on the request path so capacity and deadlines apply. This method opens a
        short-lived client for unit tests and non-session callers.
        """
        url = (base_url or self._base_url).rstrip("/")
        try:
            with gitlab.Gitlab(url=url, private_token=self._gitlab_token) as client:
                return self.select_with_client(client, project_path, iid)
        except FullDiffIncompleteError:
            raise
        except Exception as exc:
            mapped = map_gitlab_exception(
                exc,
                not_found=GitLabNotFoundContext(GitLabNotFoundKind.MERGE_REQUEST),
            )
            if mapped is not exc:
                raise mapped from None
            raise

    def select_with_client(
        self,
        client: gitlab.Gitlab,
        project_path: str,
        iid: int,
    ) -> GitLabDiffSnapshot:
        """Pin one MR diff version using an already-created SDK client.

        Exception mapping uses :func:`map_gitlab_exception` with project vs MR
        not-found context. Does not open or close the client.
        """
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

        raw_diffs: object = getattr(version, "diffs", None)
        if raw_diffs is None:
            raw_diffs = []
        if not _is_object_list(raw_diffs):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message="MR diff version diffs payload is malformed",
            )

        records: list[GitLabDiffRecord] = []
        for item in raw_diffs:
            try:
                record = item if _is_object_dict(item) else _as_dict(item)
                records.append(GitLabDiffRecord.from_mapping(record))
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


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _is_object_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _as_dict(raw: object) -> dict[str, object]:
    as_dict = getattr(raw, "asdict", None)
    if callable(as_dict):
        data = as_dict()
        if _is_object_dict(data):
            return {str(k): v for k, v in data.items()}
    attributes = getattr(raw, "attributes", None)
    if _is_object_dict(attributes):
        return {str(k): v for k, v in attributes.items()}
    if _is_object_dict(raw):
        return {str(k): v for k, v in raw.items()}
    raise ValueError("cannot coerce diff record")
