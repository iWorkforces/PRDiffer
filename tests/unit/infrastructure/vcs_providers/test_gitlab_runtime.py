"""Tests for bounded GitLab SDK runtime and status-aware exception mapping."""

from __future__ import annotations

import threading
import time
from typing import Any

import anyio
import pytest
import requests

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.domain.error_codes import (
    E1001_INVALID_URL,
    E2006_GITLAB_AUTH_FAILED,
    E2007_GITLAB_INSUFFICIENT_PERMISSIONS,
    E3006_GITLAB_RATE_LIMITED,
    E4001_REPO_NOT_FOUND,
    E4002_PR_NOT_FOUND,
    E4003_FILE_NOT_FOUND,
    E5004_TIMEOUT_ERROR,
    E5019_CONNECTION_ERROR,
    E5021_GITLAB_API_ERROR,
)
from prdiffer.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    GitLabAPIError,
    InvalidURLError,
    RateLimitError,
    TimeoutError as DomainTimeoutError,
)
from prdiffer.infrastructure.vcs_providers.gitlab_runtime import (
    GITLAB_COM_URL,
    GitLabNotFoundContext,
    GitLabNotFoundKind,
    GitLabRuntime,
    cache_host_from_base_url,
    map_gitlab_exception,
)


class FakeGitlabError(Exception):
    def __init__(self, message: str = "", response_code: int | None = None, **kwargs: Any) -> None:
        super().__init__(message)
        self.response_code = response_code
        self.error_message = message
        self.response_headers = kwargs.get("response_headers")


class FakeClient:
    """Minimal client tracking constructor args and close."""

    constructed: list[dict[str, Any]] = []
    active = 0
    max_active = 0
    closed = 0
    _lock = threading.Lock()

    def __init__(self, url: str, private_token: str | None = None, **kwargs: Any) -> None:
        self.url = url
        self.private_token = private_token
        self.kwargs = kwargs
        self.http_calls: list[dict[str, Any]] = []

        class _Session:
            def close(self) -> None:
                with FakeClient._lock:
                    FakeClient.active = max(0, FakeClient.active - 1)
                    FakeClient.closed += 1

        self.session = _Session()
        with FakeClient._lock:
            FakeClient.constructed.append(
                {
                    "url": url,
                    "private_token": private_token,
                    **kwargs,
                }
            )
            FakeClient.active += 1
            FakeClient.max_active = max(FakeClient.max_active, FakeClient.active)

    def http_request(self, *args: object, **kwargs: object) -> object:
        self.http_calls.append(dict(kwargs))
        return "ok"

    @classmethod
    def reset(cls) -> None:
        cls.constructed.clear()
        cls.active = 0
        cls.max_active = 0
        cls.closed = 0


@pytest.fixture(autouse=True)
def _reset_fake_client() -> None:
    FakeClient.reset()


def _config(**overrides: Any) -> GitLabConfig:
    base = {
        "timeout": 30,
        "max_retries": 3,
        "max_concurrent": 2,
        "retry_transient_errors": True,
        "obey_rate_limit": True,
        "pr_diff_request_timeout_seconds": 180.0,
        "allowed_hosts": ("gitlab.com", "gitlab.example.com"),
    }
    base.update(overrides)
    return GitLabConfig(**base)


@pytest.mark.unit
class TestMapGitlabException:
    def test_401_auth(self) -> None:
        mapped = map_gitlab_exception(FakeGitlabError("nope", response_code=401))
        assert isinstance(mapped, AuthenticationError)
        assert mapped.error_code is E2006_GITLAB_AUTH_FAILED
        assert "response_body" not in mapped.details

    def test_403_permission(self) -> None:
        mapped = map_gitlab_exception(FakeGitlabError("forbid", response_code=403))
        assert isinstance(mapped, AuthorizationError)
        assert mapped.error_code is E2007_GITLAB_INSUFFICIENT_PERMISSIONS

    def test_404_project(self) -> None:
        mapped = map_gitlab_exception(
            FakeGitlabError("nf", response_code=404),
            not_found=GitLabNotFoundContext(GitLabNotFoundKind.PROJECT),
        )
        assert isinstance(mapped, GitLabAPIError)
        assert mapped.error_code is E4001_REPO_NOT_FOUND

    def test_404_mr_default(self) -> None:
        mapped = map_gitlab_exception(
            FakeGitlabError("nf", response_code=404),
            not_found=GitLabNotFoundContext(GitLabNotFoundKind.MERGE_REQUEST),
        )
        assert mapped.error_code is E4002_PR_NOT_FOUND

    def test_404_file(self) -> None:
        mapped = map_gitlab_exception(
            FakeGitlabError("nf", response_code=404),
            not_found=GitLabNotFoundContext(GitLabNotFoundKind.FILE),
        )
        assert mapped.error_code is E4003_FILE_NOT_FOUND

    def test_429_rate_limit_with_retry_after(self) -> None:
        exc = FakeGitlabError("rl", response_code=429, response_headers={"Retry-After": "12"})
        mapped = map_gitlab_exception(exc, remaining_budget=30.0)
        assert isinstance(mapped, RateLimitError)
        assert mapped.error_code is E3006_GITLAB_RATE_LIMITED
        assert mapped.retry_after == 12

    def test_429_rate_limit_accepts_mixed_case_retry_after_header(self) -> None:
        exc = FakeGitlabError("rl", response_code=429, response_headers={"rEtRy-AfTeR": "12"})
        mapped = map_gitlab_exception(exc, remaining_budget=30.0)
        assert isinstance(mapped, RateLimitError)
        assert mapped.retry_after == 12

    def test_429_rate_limit_ignores_malformed_retry_after_header(self) -> None:
        exc = FakeGitlabError("rl", response_code=429, response_headers={"Retry-After": "later"})
        mapped = map_gitlab_exception(exc, remaining_budget=30.0)
        assert isinstance(mapped, RateLimitError)
        assert mapped.retry_after is None

    def test_429_rate_limit_clamps_retry_after_to_remaining_budget(self) -> None:
        exc = FakeGitlabError("rl", response_code=429, response_headers={"Retry-After": "12"})
        mapped = map_gitlab_exception(exc, remaining_budget=5.9)
        assert isinstance(mapped, RateLimitError)
        assert mapped.retry_after == 5

    def test_5xx_maps_to_e5021(self) -> None:
        mapped = map_gitlab_exception(FakeGitlabError("boom", response_code=503))
        assert isinstance(mapped, GitLabAPIError)
        assert mapped.error_code is E5021_GITLAB_API_ERROR
        assert mapped.status_code == 503

    def test_timeout_and_connection(self) -> None:
        mapped_t = map_gitlab_exception(requests.Timeout("t"))
        assert isinstance(mapped_t, DomainTimeoutError)
        assert mapped_t.error_code is E5004_TIMEOUT_ERROR

        mapped_c = map_gitlab_exception(requests.ConnectionError("c"))
        assert isinstance(mapped_c, GitLabAPIError)
        assert mapped_c.error_code is E5019_CONNECTION_ERROR

    def test_never_includes_response_body(self) -> None:
        class BodyError(FakeGitlabError):
            def __init__(self) -> None:
                super().__init__("x", response_code=500)
                self.response_body = b"secret-token=abc"

        mapped = map_gitlab_exception(BodyError())
        assert "response_body" not in mapped.details
        assert "secret" not in str(mapped.details)


@pytest.mark.unit
class TestCacheHostAndAllowlist:
    def test_cache_host_port_aware(self) -> None:
        assert cache_host_from_base_url("https://gitlab.com") == "gitlab.com"
        assert cache_host_from_base_url("https://gitlab.example.com:8443") == "gitlab.example.com:8443"
        assert cache_host_from_base_url("https://gitlab.example.com:443") == "gitlab.example.com"

    def test_cache_host_missing_hostname_fails_closed(self) -> None:
        with pytest.raises(InvalidURLError) as exc:
            cache_host_from_base_url("https://")
        assert exc.value.error_code is E1001_INVALID_URL

    def test_disallowed_host_raises_before_client(self) -> None:
        runtime = GitLabRuntime(_config(allowed_hosts=("gitlab.com",)), client_factory=FakeClient)
        with pytest.raises(InvalidURLError) as exc:
            runtime.create_client(remaining=30.0, base_url="https://evil.internal")
        assert exc.value.error_code is E1001_INVALID_URL
        assert FakeClient.constructed == []

    def test_allowed_custom_host_accepted(self) -> None:
        runtime = GitLabRuntime(
            _config(allowed_hosts=("gitlab.com", "gitlab.example.com")),
            client_factory=FakeClient,
        )
        client = runtime.create_client(remaining=30.0, base_url="https://gitlab.example.com")
        assert FakeClient.constructed[0]["url"] == "https://gitlab.example.com"
        runtime.close_client(client)


@pytest.mark.unit
class TestGitLabRuntimeClient:
    def test_create_client_exact_constructor_args(self) -> None:
        runtime = GitLabRuntime(
            _config(timeout=15, max_retries=2, retry_transient_errors=True, obey_rate_limit=True),
            private_token="tok",
            client_factory=FakeClient,
        )
        client = runtime.create_client(remaining=60.0)
        assert isinstance(client, FakeClient)
        assert FakeClient.constructed[0]["url"] == GITLAB_COM_URL
        assert FakeClient.constructed[0]["private_token"] == "tok"
        assert FakeClient.constructed[0]["timeout"] == 15
        assert FakeClient.constructed[0]["retry_transient_errors"] is True
        # max_retries injected via http_request defaults
        client.http_request("GET", "/x")
        assert client.http_calls[0]["max_retries"] == 2
        assert client.http_calls[0]["obey_rate_limit"] is True
        runtime.close_client(client)
        assert runtime.closed_client_count == 1

    def test_timeout_clamped_to_remaining(self) -> None:
        runtime = GitLabRuntime(
            _config(timeout=30),
            client_factory=FakeClient,
        )
        client = runtime.create_client(remaining=5.0)
        assert FakeClient.constructed[0]["timeout"] == 5.0
        runtime.close_client(client)

    def test_per_call_base_url_not_shared_state(self) -> None:
        runtime = GitLabRuntime(
            _config(allowed_hosts=("gitlab.com", "gitlab.example.com")),
            client_factory=FakeClient,
            base_url=GITLAB_COM_URL,
        )
        c1 = runtime.create_client(remaining=30.0, base_url="https://gitlab.example.com")
        c2 = runtime.create_client(remaining=30.0)  # default
        assert FakeClient.constructed[0]["url"] == "https://gitlab.example.com"
        assert FakeClient.constructed[1]["url"] == GITLAB_COM_URL
        runtime.close_client(c1)
        runtime.close_client(c2)


@pytest.mark.unit
@pytest.mark.anyio
class TestGitLabRuntimeAsync:
    async def test_capacity_bounds_concurrent_workers(self) -> None:
        limiter = anyio.CapacityLimiter(2)
        runtime = GitLabRuntime(
            _config(max_concurrent=2),
            client_factory=FakeClient,
            limiter=limiter,
        )
        release = threading.Event()
        peak_borrowed = 0
        deadline = time.monotonic() + 30

        def work(_client: object) -> str:
            release.wait(timeout=5)
            return "ok"

        async def run_one() -> str:
            return await runtime.run_blocking(work, deadline_monotonic=deadline)

        async def sample_borrowed() -> None:
            nonlocal peak_borrowed
            while not release.is_set():
                peak_borrowed = max(peak_borrowed, limiter.borrowed_tokens)
                await anyio.sleep(0.005)

        async with anyio.create_task_group() as tg:
            tg.start_soon(sample_borrowed)
            for _ in range(4):
                tg.start_soon(run_one)
            with anyio.fail_after(5):
                while FakeClient.active < 2:
                    await anyio.sleep(0.01)
            # While first wave is held, capacity must be exactly 2.
            assert FakeClient.active == 2
            assert FakeClient.max_active == 2
            assert limiter.borrowed_tokens == 2
            release.set()

        assert runtime.closed_client_count == 4
        assert FakeClient.max_active == 2
        assert peak_borrowed == 2

    async def test_success_and_error_close_client(self) -> None:
        runtime = GitLabRuntime(
            _config(),
            client_factory=FakeClient,
        )
        deadline = time.monotonic() + 30

        async def ok() -> int:
            return await runtime.run_blocking(lambda _c: 1, deadline_monotonic=deadline)

        assert await ok() == 1
        assert runtime.closed_client_count == 1

        def boom(_c: object) -> None:
            raise FakeGitlabError("fail", response_code=500)

        with pytest.raises(GitLabAPIError) as exc:
            await runtime.run_blocking(boom, deadline_monotonic=deadline)
        assert exc.value.error_code is E5021_GITLAB_API_ERROR
        assert runtime.closed_client_count == 2

    async def test_operation_timeout_returns_e5004(self) -> None:
        runtime = GitLabRuntime(
            _config(timeout=30, pr_diff_request_timeout_seconds=180),
            client_factory=FakeClient,
        )

        def slow(_c: object) -> str:
            time.sleep(1.0)
            return "late"

        with pytest.raises(DomainTimeoutError) as exc:
            await runtime.run_blocking(slow, deadline_monotonic=time.monotonic() + 0.05)
        assert exc.value.error_code is E5004_TIMEOUT_ERROR

    async def test_run_blocking_forwards_base_url_to_sdk(self) -> None:
        runtime = GitLabRuntime(
            _config(allowed_hosts=("gitlab.com", "gitlab.example.com")),
            private_token="tok",
            client_factory=FakeClient,
        )

        def work(client: object) -> str:
            assert isinstance(client, FakeClient)
            return client.url

        url = await runtime.run_blocking(
            work,
            base_url="https://gitlab.example.com",
            deadline_monotonic=time.monotonic() + 30,
        )
        assert url == "https://gitlab.example.com"
        assert FakeClient.constructed[0]["url"] == "https://gitlab.example.com"
        assert FakeClient.constructed[0]["private_token"] == "tok"

    async def test_per_call_deadlines_do_not_race(self) -> None:
        """Two concurrent requests with different deadlines must not share deadline state."""
        runtime = GitLabRuntime(_config(max_concurrent=2), client_factory=FakeClient)
        results: list[str] = []

        def work(_c: object) -> str:
            time.sleep(0.05)
            return "ok"

        async def short() -> None:
            with pytest.raises(DomainTimeoutError):
                await runtime.run_blocking(work, deadline_monotonic=time.monotonic() + 0.01)

        async def long() -> None:
            results.append(await runtime.run_blocking(work, deadline_monotonic=time.monotonic() + 5.0))

        async with anyio.create_task_group() as tg:
            tg.start_soon(short)
            tg.start_soon(long)

        assert results == ["ok"]

    async def test_429_does_not_locally_reattempt(self) -> None:
        """Runtime maps 429 once; no second local retry loop."""
        runtime = GitLabRuntime(
            _config(max_retries=3),
            client_factory=FakeClient,
        )
        calls = 0

        def rate_limited(_c: object) -> None:
            nonlocal calls
            calls += 1
            raise FakeGitlabError("rl", response_code=429, response_headers={"Retry-After": "5"})

        with pytest.raises(RateLimitError) as exc:
            await runtime.run_blocking(rate_limited, deadline_monotonic=time.monotonic() + 30)
        assert calls == 1
        assert exc.value.error_code is E3006_GITLAB_RATE_LIMITED
        assert runtime.closed_client_count == 1
