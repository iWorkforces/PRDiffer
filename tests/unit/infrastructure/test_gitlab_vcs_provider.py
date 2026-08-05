from threading import get_ident

import pytest

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.errors import E5002_GITHUB_API_ERROR
from prdiffer.domain.exceptions import PRDifferException
import prdiffer.infrastructure.vcs_providers.gitlab_repository as gitlab_repository
from prdiffer.infrastructure.vcs_providers.gitlab_operations import GitLabDiffRecord
from prdiffer.infrastructure.vcs_providers.gitlab_repository import GitLabVCSRepository


class RecordingOperations:
    instances: list["RecordingOperations"] = []
    diff_records: tuple[GitLabDiffRecord, ...] = ()
    latest_sha = "gitlab-sha"

    def __init__(self, token: str | None) -> None:
        self.token = token
        self.calls: list[str] = []
        self.thread_ids: list[int] = []
        self.instances.append(self)

    def initialize(self) -> None:
        self.calls.append("initialize")
        self.thread_ids.append(get_ident())

    def get_diff_records(self, owner: str, repo: str, pr: int) -> tuple[GitLabDiffRecord, ...]:
        assert (owner, repo, pr) == ("owner", "repo", 17)
        self.calls.append("diff")
        self.thread_ids.append(get_ident())
        return self.diff_records

    def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        assert (owner, repo, pr) == ("owner", "repo", 17)
        self.calls.append("sha")
        self.thread_ids.append(get_ident())
        return self.latest_sha


def install_operations(monkeypatch: pytest.MonkeyPatch, records: tuple[GitLabDiffRecord, ...] = ()) -> None:
    RecordingOperations.instances.clear()
    RecordingOperations.diff_records = records
    monkeypatch.setattr(gitlab_repository, "GitLabOperations", RecordingOperations)


class TestGitLabVCSRepository:
    def test_provider_metadata_and_url_support(self) -> None:
        # Given
        provider = GitLabVCSRepository()

        # When / Then
        assert provider.provider_name == "gitlab"
        assert provider.provider_version == "v4"
        assert provider.supports_repository("https://gitlab.com/owner/repo/-/merge_requests/17")
        assert provider.supports_repository("https://gitlab.com/group/subgroup/project/-/merge_requests/42")
        assert provider.supports_repository("https://gitlab.com/owner/repo/-/tree/abc123")
        assert not provider.supports_repository("https://github.com/owner/repo/pull/17")
        assert not provider.supports_repository("https://gitlab.com/group/../project/-/merge_requests/1")
        assert not provider.supports_repository("https://gitlab.example.com/a/b/-/merge_requests/1")

    @pytest.mark.anyio
    async def test_async_methods_use_one_worker_and_store_only_operations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        install_operations(monkeypatch)
        provider = GitLabVCSRepository("test-token")
        main_thread = get_ident()

        # When
        await provider.initialize()
        diff = await provider.get_pr_diff("owner", "repo", 17)
        sha = await provider.get_latest_commit_sha("owner", "repo", 17)

        # Then
        operation = RecordingOperations.instances[0]
        assert vars(provider) == {"_operations": operation}
        assert operation.token == "test-token"
        assert operation.calls == ["initialize", "diff", "sha"]
        assert len(operation.thread_ids) == 3
        assert all(thread_id != main_thread for thread_id in operation.thread_ids)
        assert diff == PRDiff(files=())
        assert sha == "gitlab-sha"

    @pytest.mark.anyio
    async def test_diff_mapping_preserves_gitlab_file_semantics(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        added_diff = "--- /dev/null\n+++ b/src/added.py\n+first\n+second"
        modified_diff = "--- a/src/current.py\n+++ b/src/current.py\n-old\n+new"
        renamed_diff = "--- a/src/old.py\n+++ b/src/new.py\n-old\n+new"
        deleted_diff = "--- a/src/deleted.py\n+++ /dev/null\n-old"
        records: tuple[GitLabDiffRecord, ...] = (
            GitLabDiffRecord(old_path="src/added.py", new_path="src/added.py", new_file=True, deleted_file=False, renamed_file=False, diff=added_diff),
            GitLabDiffRecord(old_path="src/current.py", new_path="src/current.py", new_file=False, deleted_file=False, renamed_file=False, diff=modified_diff),
            GitLabDiffRecord(old_path="src/old.py", new_path="src/new.py", new_file=False, deleted_file=False, renamed_file=True, diff=renamed_diff),
            GitLabDiffRecord(
                old_path="src/deleted.py", new_path="src/replacement.py", new_file=False, deleted_file=True, renamed_file=False, diff=deleted_diff
            ),
            GitLabDiffRecord(old_path="src/collapsed.py", new_path="src/collapsed.py", new_file=False, deleted_file=False, renamed_file=False, collapsed=True),
            GitLabDiffRecord(old_path="src/large.py", new_path="src/large.py", new_file=False, deleted_file=False, renamed_file=False, too_large=True),
        )
        install_operations(monkeypatch, records)

        # When
        diff = await GitLabVCSRepository().get_pr_diff("owner", "repo", 17)

        # Then
        assert diff == PRDiff(
            files=(
                FileDiffResponse("src/added.py", EDIT_TYPE.ADDED, FileStats(additions=2, deletions=0), added_diff),
                FileDiffResponse("src/current.py", EDIT_TYPE.MODIFIED, FileStats(additions=1, deletions=1), modified_diff),
                FileDiffResponse(
                    "src/new.py",
                    EDIT_TYPE.RENAMED,
                    FileStats(additions=1, deletions=1),
                    renamed_diff,
                    "src/old.py",
                ),
                FileDiffResponse("src/deleted.py", EDIT_TYPE.DELETED, FileStats(additions=0, deletions=1), deleted_diff),
                FileDiffResponse("src/collapsed.py", EDIT_TYPE.MODIFIED, FileStats(), ""),
                FileDiffResponse("src/large.py", EDIT_TYPE.MODIFIED, FileStats(), ""),
            )
        )

    @pytest.mark.anyio
    async def test_diff_mapping_normalizes_null_collapsed_and_too_large_patches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        records = (
            GitLabDiffRecord(
                old_path="src/collapsed.py", new_path="src/collapsed.py", new_file=False, deleted_file=False, renamed_file=False, collapsed=True, diff=None
            ),
            GitLabDiffRecord(
                old_path="src/large.py", new_path="src/large.py", new_file=False, deleted_file=False, renamed_file=False, too_large=True, diff=None
            ),
        )
        install_operations(monkeypatch, records)

        # When
        diff = await GitLabVCSRepository().get_pr_diff("owner", "repo", 17)

        # Then
        assert diff == PRDiff(
            files=(
                FileDiffResponse("src/collapsed.py", EDIT_TYPE.MODIFIED, FileStats(), ""),
                FileDiffResponse("src/large.py", EDIT_TYPE.MODIFIED, FileStats(), ""),
            )
        )

    @pytest.mark.anyio
    async def test_conflicting_diff_flags_raise_existing_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        records = (GitLabDiffRecord(old_path="src/file.py", new_path="src/file.py", new_file=True, deleted_file=True, renamed_file=False),)
        install_operations(monkeypatch, records)

        # When / Then
        with pytest.raises(PRDifferException) as error:
            await GitLabVCSRepository().get_pr_diff("owner", "repo", 17)

        assert error.value.message == "GitLab diff record has conflicting change flags"
        assert error.value.error_code is E5002_GITHUB_API_ERROR
