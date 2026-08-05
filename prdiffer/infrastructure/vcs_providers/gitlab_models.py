"""Frozen boundary models for GitLab strict full-diff acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeGuard


@dataclass(frozen=True, slots=True)
class GitLabDiffRefs:
    """Immutable MR comparison refs (base/start/head)."""

    base_sha: str
    start_sha: str
    head_sha: str

    @classmethod
    def from_mapping(cls, raw: object) -> GitLabDiffRefs:
        if not _is_object_dict(raw):
            raise ValueError("diff_refs must be a mapping")
        base = raw.get("base_sha")
        start = raw.get("start_sha")
        head = raw.get("head_sha")
        if not isinstance(base, str) or not base:
            raise ValueError("diff_refs.base_sha missing")
        if not isinstance(start, str) or not start:
            raise ValueError("diff_refs.start_sha missing")
        if not isinstance(head, str) or not head:
            raise ValueError("diff_refs.head_sha missing")
        return cls(base_sha=base, start_sha=start, head_sha=head)


@dataclass(frozen=True, slots=True)
class GitLabVersionSummary:
    """One listed merge-request diff version summary."""

    version_id: int
    base_commit_sha: str
    start_commit_sha: str
    head_commit_sha: str

    @classmethod
    def from_object(cls, raw: object) -> GitLabVersionSummary:
        data = _attrs(raw)
        raw_id = data.get("id")
        version_id: int
        if isinstance(raw_id, int) and not isinstance(raw_id, bool):
            version_id = raw_id
        elif isinstance(raw_id, str) and raw_id.isdigit():
            version_id = int(raw_id)
        else:
            raise ValueError("version id missing or invalid")
        base = data.get("base_commit_sha")
        start = data.get("start_commit_sha")
        head = data.get("head_commit_sha")
        if not isinstance(base, str) or not base:
            raise ValueError("version base_commit_sha missing")
        if not isinstance(start, str) or not start:
            raise ValueError("version start_commit_sha missing")
        if not isinstance(head, str) or not head:
            raise ValueError("version head_commit_sha missing")
        return cls(
            version_id=version_id,
            base_commit_sha=base,
            start_commit_sha=start,
            head_commit_sha=head,
        )

    def matches_refs(self, refs: GitLabDiffRefs) -> bool:
        return self.base_commit_sha == refs.base_sha and self.start_commit_sha == refs.start_sha and self.head_commit_sha == refs.head_sha


@dataclass(frozen=True, slots=True)
class GitLabDiffRecord:
    """One ordered file change from a fetched diff version."""

    old_path: str
    new_path: str
    new_file: bool
    deleted_file: bool
    renamed_file: bool
    a_mode: str | None = None
    b_mode: str | None = None
    diff: str | None = None
    collapsed: bool = False
    too_large: bool = False
    generated_file: bool | None = None

    @classmethod
    def from_mapping(cls, raw: object) -> GitLabDiffRecord:
        if not _is_object_dict(raw):
            raise ValueError("diff record must be a mapping")
        old_path = raw.get("old_path")
        new_path = raw.get("new_path")
        if not isinstance(old_path, str) or not isinstance(new_path, str):
            raise ValueError("diff record paths must be strings")
        return cls(
            old_path=old_path,
            new_path=new_path,
            new_file=bool(raw.get("new_file", False)),
            deleted_file=bool(raw.get("deleted_file", False)),
            renamed_file=bool(raw.get("renamed_file", False)),
            a_mode=_optional_str(raw.get("a_mode")),
            b_mode=_optional_str(raw.get("b_mode")),
            diff=_optional_str_or_none(raw.get("diff")),
            collapsed=bool(raw.get("collapsed", False)),
            too_large=bool(raw.get("too_large", False)),
            generated_file=_optional_bool(raw.get("generated_file")),
        )


@dataclass(frozen=True, slots=True)
class GitLabDiffSnapshot:
    """Pinned MR diff version: identity + ordered embedded records."""

    project_path: str
    iid: int
    version_id: int
    base_sha: str
    start_sha: str
    head_sha: str
    state: str
    real_size: int | None
    records: tuple[GitLabDiffRecord, ...]


def _is_object_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _attrs(raw: object) -> dict[str, object]:
    if _is_object_dict(raw):
        return {str(k): v for k, v in raw.items()}
    # python-gitlab RESTObject attributes
    as_dict = getattr(raw, "asdict", None)
    if callable(as_dict):
        data = as_dict()
        if _is_object_dict(data):
            return {str(k): v for k, v in data.items()}
    attributes = getattr(raw, "attributes", None)
    if _is_object_dict(attributes):
        return {str(k): v for k, v in attributes.items()}
    # Fallback: public non-callable attributes
    return {k: getattr(raw, k) for k in dir(raw) if not k.startswith("_") and not callable(getattr(raw, k, None))}


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _optional_str_or_none(value: object) -> str | None:
    """Preserve explicit null diffs as None; coerce other values to str."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)
