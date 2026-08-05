"""Legacy pagination tests replaced by immutable version selection.

Strict full-diff no longer uses current `/diffs` or manual page fallbacks.
"""

from __future__ import annotations

import pytest

from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
import prdiffer.infrastructure.vcs_providers.gitlab_operations as gitlab_operations
from prdiffer.infrastructure.vcs_providers.gitlab_operations import GitLabOperations
from tests.unit.infrastructure.test_gitlab_operations import (
    FakeGitLab,
    FakeMergeRequests,
    FakeProject,
    FakeProjects,
    _payload,
    _version,
    install,
)


@pytest.mark.unit
class TestNoCurrentDiffsEndpoint:
    def test_never_calls_current_file_diffs_list_on_mr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        refs = {"base_sha": "b", "start_sha": "s", "head_sha": "h"}
        versions = [_version(3, "b", "s", "h")]
        payloads = {3: _payload(3, "b", "s", "h")}
        mr = FakeMergeRequests(diff_refs=refs, versions=versions, version_payloads=payloads)
        client = FakeGitLab(FakeProjects(FakeProject(mr)))
        install(monkeypatch, client)

        GitLabOperations().get_diff_records("owner", "repo", 17)

        # Only version list + version get; no http_list to /diffs
        assert mr.diffs.list_calls == 1
        assert mr.diffs.get_calls == [3]
        assert not hasattr(client, "http_list") or not getattr(client, "http_list_calls", None)

    def test_get_diff_records_uses_pinned_version_records(self, monkeypatch: pytest.MonkeyPatch) -> None:
        refs = {"base_sha": "b", "start_sha": "s", "head_sha": "h"}
        diffs = [
            {
                "old_path": "one.py",
                "new_path": "one.py",
                "a_mode": "100644",
                "b_mode": "100644",
                "new_file": False,
                "deleted_file": False,
                "renamed_file": False,
                "diff": "+x",
                "collapsed": False,
                "too_large": False,
            },
            {
                "old_path": "two.py",
                "new_path": "two.py",
                "a_mode": "100644",
                "b_mode": "100644",
                "new_file": True,
                "deleted_file": False,
                "renamed_file": False,
                "diff": "+y",
                "collapsed": False,
                "too_large": False,
            },
        ]
        versions = [_version(1, "b", "s", "h")]
        payloads = {1: _payload(1, "b", "s", "h", real_size=2, diffs=diffs)}
        mr = FakeMergeRequests(diff_refs=refs, versions=versions, version_payloads=payloads)
        install(monkeypatch, FakeGitLab(FakeProjects(FakeProject(mr))))

        records = GitLabOperations().get_diff_records("owner", "repo", 17)
        assert [r.new_path for r in records] == ["one.py", "two.py"]
        assert records[1].new_file is True

    def test_incomplete_selection_raises_before_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        refs = {"base_sha": "b", "start_sha": "s", "head_sha": "h"}
        mr = FakeMergeRequests(diff_refs=refs, versions=[], version_payloads={})
        install(monkeypatch, FakeGitLab(FakeProjects(FakeProject(mr))))
        with pytest.raises(FullDiffIncompleteError) as exc:
            GitLabOperations().get_diff_records("o", "r", 1)
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED
