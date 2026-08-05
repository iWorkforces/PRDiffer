import pytest

from prdiffer.domain.errors import E4002_PR_NOT_FOUND, E5002_GITHUB_API_ERROR
from prdiffer.domain.exceptions import PRDifferException
import prdiffer.infrastructure.vcs_providers.gitlab_operations as gitlab_operations
from prdiffer.infrastructure.vcs_providers.gitlab_operations import GitLabDiffRecord, GitLabOperations


class FakeGitLab:
    def __init__(self, responses: list[list[dict[str, object]] | BaseException]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, dict[str, int | bool]]] = []
        self.events: list[str] = []

    def __enter__(self) -> "FakeGitLab":
        self.events.append("enter")
        return self

    def __exit__(self, *_: object) -> None:
        self.events.append("exit")

    def http_list(self, path: str, **kwargs: int | bool) -> list[dict[str, object]]:
        self.calls.append((path, dict(kwargs)))
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class GitLabFactory:
    def __init__(self, client: FakeGitLab) -> None:
        self.client = client
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, *, url: str, private_token: str | None) -> FakeGitLab:
        self.calls.append((url, private_token))
        return self.client


def diff_record(path: str) -> dict[str, object]:
    return {"old_path": path, "new_path": path, "new_file": False, "deleted_file": False, "renamed_file": False}


def install_client(monkeypatch: pytest.MonkeyPatch, client: FakeGitLab) -> None:
    monkeypatch.setattr(gitlab_operations.gitlab, "Gitlab", GitLabFactory(client))


class TestGitLabDiffPagination:
    def test_diff_uses_the_structured_endpoint_with_initial_aggregate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        records = [diff_record("src/one.py"), diff_record("src/two.py")]
        client = FakeGitLab([records])
        install_client(monkeypatch, client)

        # When
        result = GitLabOperations("test-token").get_diff_records("owner", "repo", 17)

        # Then
        assert result == tuple(GitLabDiffRecord.model_validate(record) for record in records)
        assert client.calls == [("/projects/owner%2Frepo/merge_requests/17/diffs", {"get_all": True, "per_page": 100, "unidiff": True})]
        assert client.events == ["enter", "exit"]

    def test_diff_fallback_starts_after_aggregated_pages_and_preserves_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        initial = [diff_record(f"src/initial-{index}.py") for index in range(200)]
        explicit_page = [diff_record(f"src/explicit-{index}.py") for index in range(100)]
        final_page = [diff_record("src/final.py")]
        client = FakeGitLab([initial, explicit_page, final_page])
        install_client(monkeypatch, client)

        # When
        result = GitLabOperations().get_diff_records("owner", "repo", 17)

        # Then
        assert result == tuple(GitLabDiffRecord.model_validate(record) for record in initial + explicit_page + final_page)
        assert client.calls == [
            ("/projects/owner%2Frepo/merge_requests/17/diffs", {"get_all": True, "per_page": 100, "unidiff": True}),
            ("/projects/owner%2Frepo/merge_requests/17/diffs", {"page": 3, "get_all": False, "per_page": 100, "unidiff": True}),
            ("/projects/owner%2Frepo/merge_requests/17/diffs", {"page": 4, "get_all": False, "per_page": 100, "unidiff": True}),
        ]

    @pytest.mark.parametrize("initial", [[], [diff_record("src/file.py")]])
    def test_diff_does_not_probe_after_empty_or_short_initial_response(self, monkeypatch: pytest.MonkeyPatch, initial: list[dict[str, object]]) -> None:
        # Given
        client = FakeGitLab([initial])
        install_client(monkeypatch, client)

        # When
        result = GitLabOperations().get_diff_records("owner", "repo", 17)

        # Then
        assert result == tuple(GitLabDiffRecord.model_validate(record) for record in initial)
        assert len(client.calls) == 1

    @pytest.mark.parametrize(
        ("sdk_error", "expected_message", "expected_code"),
        [
            (gitlab_operations.gitlab.GitlabHttpError("token=secret"), "Merge request not found", E4002_PR_NOT_FOUND),
            (gitlab_operations.gitlab.GitlabParsingError("token=secret"), "GitLab API error", E5002_GITHUB_API_ERROR),
        ],
    )
    def test_diff_errors_are_sanitized(self, monkeypatch: pytest.MonkeyPatch, sdk_error: BaseException, expected_message: str, expected_code: object) -> None:
        # Given
        client = FakeGitLab([sdk_error])
        install_client(monkeypatch, client)

        # When / Then
        with pytest.raises(PRDifferException) as error:
            GitLabOperations().get_diff_records("owner", "repo", 17)

        assert error.value.message == expected_message
        assert error.value.error_code is expected_code
        assert error.value.details == {}
        assert "secret" not in str(error.value)
