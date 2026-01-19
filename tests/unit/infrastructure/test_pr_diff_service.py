import pytest

from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from ccpragents.infrastructure.services.pr_diff_service import GitHubPRDiffService


class DummyGitHubAPI:
    def initialize_client(self, github_token=None, timeout=30):
        return None

    def get_repository(self, repo_full_name):
        return object()

    def get_pull_request(self, repository, pr_number):
        return DummyPullRequest()


class DummyHead:
    def __init__(self, sha):
        self.sha = sha


class DummyPullRequest:
    def __init__(self):
        self.head = DummyHead("dummy-sha")


@pytest.mark.asyncio
async def test_get_pr_diff_populates_metadata_and_summaries(monkeypatch):
    service = GitHubPRDiffService(
        github_api_client=DummyGitHubAPI(),
        diff_generator=None,
        file_processor=None,
        logger=None,
    )

    diff_files = [
        FilePatchInfo(
            filename="auth/config.py",
            patch="+ # TODO: add validation",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=10,
            num_minus_lines=2,
        )
    ]

    monkeypatch.setattr(
        service,
        "_generate_diff_content",
        lambda *_: ("x" * 50, diff_files),
    )
    monkeypatch.setattr(service, "_get_commit_messages", lambda *_: "msg")

    service._diff_truncate_enabled = True
    service._diff_max_total_chars = 10
    service._diff_truncation_notice = "[TRUNC]"

    result = await service.get_pr_diff("owner", "repo", 1)

    assert result is not None
    assert result.files_changed == 1
    assert result.total_additions == 10
    assert result.total_deletions == 2
    assert result.generation_metadata["files_processed"] == 1
    assert result.generation_metadata["diff_truncated"] is True
    assert result.diff_content.endswith("[TRUNC]")
    assert result.file_summaries is not None
    assert "Contains TODO comments" in result.file_summaries[0]["code_smell_indicators"]
    assert result.file_summaries[0]["review_priority"] == "high"


@pytest.mark.asyncio
async def test_get_latest_commit_sha_uses_head_sha():
    service = GitHubPRDiffService(
        github_api_client=DummyGitHubAPI(),
        diff_generator=None,
        file_processor=None,
        logger=None,
    )

    sha = await service.get_latest_commit_sha("owner", "repo", 1)
    assert sha == "dummy-sha"
