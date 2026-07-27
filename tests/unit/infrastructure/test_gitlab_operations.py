import pytest

from prdiffer.domain.errors import E4002_PR_NOT_FOUND, E5002_GITHUB_API_ERROR, E5019_CONNECTION_ERROR
from prdiffer.domain.exceptions import PRDifferException
import prdiffer.infrastructure.vcs_providers.gitlab_operations as gitlab_operations
from prdiffer.infrastructure.vcs_providers.gitlab_operations import GitLabOperations


class FakeMergeRequests:
    def __init__(self, sha: object, sha_is_present: bool = True) -> None:
        self._sha = sha
        self._sha_is_present = sha_is_present
        self.calls: list[int] = []

    def get(self, number: int) -> object:
        self.calls.append(number)
        attributes = {"sha": self._sha} if self._sha_is_present else {}
        return type("MergeRequest", (), attributes)()


class FakeProject:
    def __init__(self, sha: object, sha_is_present: bool = True) -> None:
        self.mergerequests = FakeMergeRequests(sha, sha_is_present)


class FakeProjects:
    def __init__(self, project: FakeProject, error: BaseException | None = None) -> None:
        self._project = project
        self._error = error
        self.calls: list[str] = []

    def get(self, identifier: str) -> FakeProject:
        self.calls.append(identifier)
        if self._error is not None:
            raise self._error
        return self._project


class FakeGitLab:
    def __init__(self, sha: object = "latest-sha", error: BaseException | None = None, sha_is_present: bool = True) -> None:
        self.events: list[str] = []
        self.auth_error = error
        self.project = FakeProject(sha, sha_is_present)
        self.projects = FakeProjects(self.project, error)

    def __enter__(self) -> "FakeGitLab":
        self.events.append("enter")
        return self

    def __exit__(self, *_: object) -> None:
        self.events.append("exit")

    def auth(self) -> None:
        self.events.append("auth")
        if self.auth_error is not None:
            raise self.auth_error


class GitLabFactory:
    def __init__(self, clients: list[FakeGitLab]) -> None:
        self._clients = clients
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, *, url: str, private_token: str | None) -> FakeGitLab:
        self.calls.append((url, private_token))
        return self._clients.pop(0)


def install_client_factory(monkeypatch: pytest.MonkeyPatch, factory: GitLabFactory) -> None:
    monkeypatch.setattr(gitlab_operations.gitlab, "Gitlab", factory)


class TestGitLabOperations:
    def test_initialize_creates_authenticates_and_disposes_a_fresh_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        auth_client = FakeGitLab()
        sha_client = FakeGitLab()
        factory = GitLabFactory([auth_client, sha_client])
        install_client_factory(monkeypatch, factory)
        operations = GitLabOperations("test-token")
        assert factory.calls == []

        # When
        operations.initialize()
        operations.get_latest_commit_sha("owner", "repo", 17)

        # Then
        assert factory.calls == [("https://gitlab.com", "test-token"), ("https://gitlab.com", "test-token")]
        assert auth_client.events == ["enter", "auth", "exit"]
        assert sha_client.events == ["enter", "exit"]

    def test_sha_lookup_uses_project_and_merge_request_managers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        client = FakeGitLab("head-sha")
        factory = GitLabFactory([client])
        install_client_factory(monkeypatch, factory)

        # When
        sha = GitLabOperations().get_latest_commit_sha("owner", "repo", 17)

        # Then
        assert sha == "head-sha"
        assert factory.calls == [("https://gitlab.com", None)]
        assert client.projects.calls == ["owner/repo"]
        assert client.project.mergerequests.calls == [17]
        assert client.events == ["enter", "exit"]

    def test_sha_lookup_sanitizes_an_absent_merge_request_sha(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        client = FakeGitLab(sha_is_present=False)
        install_client_factory(monkeypatch, GitLabFactory([client]))

        # When / Then
        with pytest.raises(PRDifferException) as error:
            GitLabOperations().get_latest_commit_sha("owner", "repo", 17)

        assert error.value.message == "Merge request SHA is missing"
        assert error.value.error_code is E5002_GITHUB_API_ERROR
        assert client.events == ["enter", "exit"]

    @pytest.mark.parametrize("sha", (None, "", 17), ids=("null", "empty", "non-string"))
    def test_sha_lookup_sanitizes_invalid_merge_request_sha(self, monkeypatch: pytest.MonkeyPatch, sha: object) -> None:
        # Given
        client = FakeGitLab(sha)
        install_client_factory(monkeypatch, GitLabFactory([client]))

        # When / Then
        with pytest.raises(PRDifferException) as error:
            GitLabOperations().get_latest_commit_sha("owner", "repo", 17)

        assert error.value.message == "Merge request SHA is missing"
        assert error.value.error_code is E5002_GITHUB_API_ERROR
        assert client.events == ["enter", "exit"]

    def test_initialize_sanitizes_documented_connection_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        client = FakeGitLab(error=gitlab_operations.gitlab.GitlabConnectionError("token=secret"))
        install_client_factory(monkeypatch, GitLabFactory([client]))

        # When / Then
        with pytest.raises(PRDifferException) as error:
            GitLabOperations().initialize()

        assert error.value.message == "Failed to initialize GitLab connection"
        assert error.value.error_code is E5019_CONNECTION_ERROR
        assert error.value.details == {}
        assert "secret" not in str(error.value)
        assert client.events == ["enter", "auth", "exit"]

    def test_sha_lookup_sanitizes_not_found_and_read_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        missing_client = FakeGitLab(error=gitlab_operations.gitlab.GitlabGetError("response=secret"))
        parsing_client = FakeGitLab(error=gitlab_operations.gitlab.GitlabParsingError("response=secret"))
        install_client_factory(monkeypatch, GitLabFactory([missing_client, parsing_client]))
        operations = GitLabOperations()

        # When / Then
        with pytest.raises(PRDifferException) as missing_error:
            operations.get_latest_commit_sha("owner", "repo", 17)
        with pytest.raises(PRDifferException) as parsing_error:
            operations.get_latest_commit_sha("owner", "repo", 17)

        assert missing_error.value.message == "Merge request not found"
        assert missing_error.value.error_code is E4002_PR_NOT_FOUND
        assert parsing_error.value.message == "GitLab API error"
        assert parsing_error.value.error_code is E5002_GITHUB_API_ERROR
        assert "secret" not in str(missing_error.value)
        assert "secret" not in str(parsing_error.value)
        assert missing_client.events == ["enter", "exit"]
        assert parsing_client.events == ["enter", "exit"]
