import pytest

from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService


class DummyGitHubAPI:
    def initialize_client(self, github_token=None, timeout=30):
        return None

    def get_repository(self, repo_full_name):
        return object()

    def get_pull_request(self, repository, pr_number):
        return DummyPullRequest()

    def _get_pygithub_repository(self, repo_full_name):
        return object()

    def _get_pygithub_pull_request(self, repository, pr_number):
        return DummyPullRequest()


class DummyHead:
    def __init__(self, sha):
        self.sha = sha


class DummyPullRequest:
    def __init__(self):
        self.head = DummyHead("dummy-sha")


@pytest.mark.asyncio
async def test_get_pr_diff_with_truncation(monkeypatch):
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
        lambda *_: diff_files,
    )

    service._diff_truncate_enabled = True
    service._diff_max_total_chars = 10
    service._diff_truncation_notice = "[TRUNC]"

    result = await service.get_pr_diff("owner", "repo", 1)

    assert result is not None
    # PRDiff now uses files list structure
    assert isinstance(result.files, list)


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
