"""Tests for GitLab pinned typed file content acquisition."""

from __future__ import annotations

from typing import Any

import pytest

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.vcs_providers.gitlab_content import GitLabContentFetcher
from prdiffer.infrastructure.vcs_providers.gitlab_inventory import GitLabInventoryFile
from prdiffer.infrastructure.vcs_providers.gitlab_models import GitLabDiffRecord, GitLabDiffSnapshot
from prdiffer.infrastructure.vcs_providers.gitlab_runtime import GitLabRuntime


class FakeFiles:
    def __init__(self, store: dict[tuple[str, str], bytes | BaseException]) -> None:
        self.store = store
        self.calls: list[tuple[str, str]] = []

    def raw(self, file_path: str, ref: str) -> bytes:
        self.calls.append((file_path, ref))
        value = self.store.get((file_path, ref))
        if value is None:
            import gitlab

            raise gitlab.GitlabGetError("nf", response_code=404)
        if isinstance(value, BaseException):
            raise value
        return value


class FakeProject:
    def __init__(self, files: FakeFiles) -> None:
        self.files = files


class FakeProjects:
    def __init__(self, project: FakeProject) -> None:
        self._project = project
        self.calls: list[str] = []

    def get(self, path: str) -> FakeProject:
        self.calls.append(path)
        return self._project


class FakeClient:
    def __init__(self, store: dict[tuple[str, str], bytes | BaseException]) -> None:
        self.files = FakeFiles(store)
        self.projects = FakeProjects(FakeProject(self.files))
        self.session = type("S", (), {"close": lambda self: None})()


def _runtime(store: dict[tuple[str, str], bytes | BaseException], **cfg: Any) -> tuple[GitLabRuntime, FakeClient]:
    client = FakeClient(store)
    config = GitLabConfig(max_file_size_bytes=cfg.get("max_file_size_bytes", 10_485_760), max_concurrent=cfg.get("max_concurrent", 4))
    runtime = GitLabRuntime(config, client_factory=lambda *a, **k: client)
    return runtime, client


def _snap(**kwargs: Any) -> GitLabDiffSnapshot:
    return GitLabDiffSnapshot(
        project_path=kwargs.get("project_path", "g/p"),
        iid=1,
        version_id=1,
        base_sha=kwargs.get("base_sha", "base"),
        start_sha="start",
        head_sha=kwargs.get("head_sha", "head"),
        state="collected",
        real_size=kwargs.get("real_size", 1),
        records=kwargs.get("records", ()),
    )


def _item(edit: EDIT_TYPE, old: str, new: str, index: int = 0) -> GitLabInventoryFile:
    return GitLabInventoryFile(
        record=GitLabDiffRecord(
            old_path=old,
            new_path=new,
            new_file=edit is EDIT_TYPE.ADDED,
            deleted_file=edit is EDIT_TYPE.DELETED,
            renamed_file=edit is EDIT_TYPE.RENAMED,
        ),
        edit_type=edit,
        index=index,
    )


@pytest.mark.unit
@pytest.mark.anyio
class TestGitLabContentFetcher:
    async def test_added_deleted_renamed_modified_path_ref_matrix(self) -> None:
        store: dict[tuple[str, str], bytes | BaseException] = {
            ("new.py", "head"): b"new",
            ("gone.py", "base"): b"old",
            ("old.py", "base"): b"rename-old",
            ("ren.py", "head"): b"rename-new",
            ("mod.py", "base"): b"before",
            ("mod.py", "head"): b"after",
        }
        runtime, client = _runtime(store)
        fetcher = GitLabContentFetcher(runtime, runtime.config, parallel_enabled=True)
        inv = (
            _item(EDIT_TYPE.ADDED, "new.py", "new.py", 0),
            _item(EDIT_TYPE.DELETED, "gone.py", "gone.py", 1),
            _item(EDIT_TYPE.RENAMED, "old.py", "ren.py", 2),
            _item(EDIT_TYPE.MODIFIED, "mod.py", "mod.py", 3),
        )
        snap = _snap(real_size=4)
        results = await fetcher.fetch_all(snap, inv)
        assert len(results) == 4
        assert results[0].base.text == "" and results[0].head.text == "new"
        assert results[1].base.text == "old" and results[1].head.text == ""
        assert results[2].base.text == "rename-old" and results[2].head.text == "rename-new"
        assert results[3].base.text == "before" and results[3].head.text == "after"
        # Path/ref matrix
        assert ("new.py", "head") in client.files.calls
        assert ("gone.py", "base") in client.files.calls
        assert ("old.py", "base") in client.files.calls
        assert ("ren.py", "head") in client.files.calls

    async def test_zero_byte_available(self) -> None:
        store: dict[tuple[str, str], bytes | BaseException] = {("e.py", "head"): b""}
        runtime, _ = _runtime(store)
        fetcher = GitLabContentFetcher(runtime, runtime.config, parallel_enabled=False)
        results = await fetcher.fetch_all(_snap(), (_item(EDIT_TYPE.ADDED, "e.py", "e.py"),))
        assert results[0].head.text == ""

    async def test_required_404_content_unavailable(self) -> None:
        runtime, _ = _runtime({})
        fetcher = GitLabContentFetcher(runtime, runtime.config, parallel_enabled=False)
        with pytest.raises(FullDiffIncompleteError) as exc:
            await fetcher.fetch_all(_snap(), (_item(EDIT_TYPE.MODIFIED, "m.py", "m.py"),))
        assert exc.value.reason is FullDiffIncompleteReason.CONTENT_UNAVAILABLE

    async def test_fetch_forwards_base_url_to_runtime_client(self) -> None:
        """Content fetch must construct SDK clients with the per-request base_url."""
        store: dict[tuple[str, str], bytes | BaseException] = {("a.py", "head"): b"x"}
        constructed: list[str] = []

        def factory(url: str, private_token: str | None = None, **kwargs: object) -> FakeClient:
            constructed.append(url)
            return FakeClient(store)

        config = GitLabConfig(allowed_hosts=("gitlab.com", "gitlab.example.com"), max_concurrent=1)
        runtime = GitLabRuntime(config, client_factory=factory)
        fetcher = GitLabContentFetcher(runtime, config, parallel_enabled=False)
        await fetcher.fetch_all(
            _snap(),
            (_item(EDIT_TYPE.ADDED, "a.py", "a.py"),),
            base_url="https://gitlab.example.com",
            deadline_monotonic=None,
        )
        assert constructed
        assert all(u == "https://gitlab.example.com" for u in constructed)

    async def test_oversized_binary_decode(self) -> None:
        runtime, _ = _runtime({("b.py", "base"): b"x" * 11, ("b.py", "head"): b"y"}, max_file_size_bytes=10)
        fetcher = GitLabContentFetcher(runtime, runtime.config, parallel_enabled=False)
        with pytest.raises(FullDiffIncompleteError) as exc:
            await fetcher.fetch_all(_snap(), (_item(EDIT_TYPE.MODIFIED, "b.py", "b.py"),))
        assert exc.value.reason is FullDiffIncompleteReason.FILE_SIZE_LIMIT

        runtime2, _ = _runtime({("n.py", "base"): b"a\x00b", ("n.py", "head"): b"c"})
        fetcher2 = GitLabContentFetcher(runtime2, runtime2.config, parallel_enabled=False)
        with pytest.raises(FullDiffIncompleteError) as exc2:
            await fetcher2.fetch_all(_snap(), (_item(EDIT_TYPE.MODIFIED, "n.py", "n.py"),))
        assert exc2.value.reason is FullDiffIncompleteReason.BINARY_CONTENT

        runtime3, _ = _runtime({("u.py", "base"): b"\xff\xfe", ("u.py", "head"): b"ok"})
        fetcher3 = GitLabContentFetcher(runtime3, runtime3.config, parallel_enabled=False)
        with pytest.raises(FullDiffIncompleteError) as exc3:
            await fetcher3.fetch_all(_snap(), (_item(EDIT_TYPE.MODIFIED, "u.py", "u.py"),))
        assert exc3.value.reason is FullDiffIncompleteReason.CONTENT_DECODE_FAILED
