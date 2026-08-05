from __future__ import annotations

import anyio
import pytest

from prdiffer.domain.entities.file_content import FileContentAvailable, FileContentRequest, FileContentResponse, FileContentResult
from prdiffer.infrastructure.github.client import GitHubAPIClient
from prdiffer.infrastructure.utils.parallel.results import IndexedBatchError


@pytest.mark.unit
def test_multi_ref_batch_returns_ref_qualified_results_in_request_order() -> None:
    requests = (
        FileContentRequest("owner/repository", "src/module.py", "head-sha"),
        FileContentRequest("owner/repository", "src/module.py", "base-sha"),
    )
    client = GitHubAPIClient(max_concurrent=2, parallel_file_fetch_enabled=True)

    async def fetch(request: FileContentRequest) -> FileContentResult:
        return FileContentAvailable(text=f"{request.ref}:{request.path}")

    client._get_file_content_request_async = fetch

    responses: tuple[FileContentResponse, ...] = client.get_files_content_multi_ref_batch(requests)

    assert tuple(response.request for response in responses) == requests
    assert tuple(response.content for response in responses) == (
        FileContentAvailable(text="head-sha:src/module.py"),
        FileContentAvailable(text="base-sha:src/module.py"),
    )


@pytest.mark.unit
def test_multi_ref_batch_uses_one_capacity_bound_for_all_refs() -> None:
    requests = tuple(FileContentRequest("owner/repository", f"src/{index}.py", ref) for index, ref in enumerate(("head", "base", "head", "base")))
    client = GitHubAPIClient(max_concurrent=2, parallel_file_fetch_enabled=True)
    active = 0
    peak_active = 0

    async def fetch(request: FileContentRequest) -> FileContentResult:
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        try:
            await anyio.lowlevel.checkpoint()
            return FileContentAvailable(text=request.ref)
        finally:
            active -= 1

    client._get_file_content_request_async = fetch

    responses = client.get_files_content_multi_ref_batch(requests)

    assert tuple(response.request for response in responses) == requests
    assert peak_active == 2


@pytest.mark.unit
def test_multi_ref_batch_preserves_mixed_cache_hit_miss_order_and_ref_identity() -> None:
    head = FileContentRequest("owner/repository", "src/module.py", "head")
    base = FileContentRequest("owner/repository", "src/module.py", "base")
    miss = FileContentRequest("owner/repository", "src/other.py", "head")
    requests = (base, miss, head)
    client = GitHubAPIClient(max_concurrent=2, parallel_file_fetch_enabled=True)
    client._cache_set_available(client._content_cache_key(head.repo_full_name, head.path, head.ref), "cached-head")
    client._cache_set_available(client._content_cache_key(base.repo_full_name, base.path, base.ref), "cached-base")
    fetched_requests: list[FileContentRequest] = []

    async def fetch(request: FileContentRequest) -> FileContentResult:
        fetched_requests.append(request)
        return FileContentAvailable(text="fetched-miss")

    client._get_file_content_request_async = fetch

    responses = client.get_files_content_multi_ref_batch(requests)

    assert tuple(response.request for response in responses) == requests
    assert tuple(response.content for response in responses) == (
        FileContentAvailable(text="cached-base"),
        FileContentAvailable(text="fetched-miss"),
        FileContentAvailable(text="cached-head"),
    )
    assert fetched_requests == [miss]


@pytest.mark.unit
def test_multi_ref_batch_raises_without_returning_partial_results_on_operational_failure() -> None:
    requests = (
        FileContentRequest("owner/repository", "src/healthy.py", "head"),
        FileContentRequest("owner/repository", "src/failing.py", "base"),
    )
    client = GitHubAPIClient(max_concurrent=2, parallel_file_fetch_enabled=True)
    healthy_finished = anyio.Event()

    async def fetch(request: FileContentRequest) -> FileContentResult:
        if request.path == "src/healthy.py":
            healthy_finished.set()
            return FileContentAvailable(text="healthy")
        await healthy_finished.wait()
        if request.path == "src/failing.py":
            raise RuntimeError("upstream unavailable")
        raise AssertionError("unexpected request")

    client._get_file_content_request_async = fetch

    with pytest.raises(IndexedBatchError) as error_info:
        client.get_files_content_multi_ref_batch(requests)

    error = error_info.value
    assert tuple(outcome.key for outcome in error.outcomes) == requests
    assert tuple(outcome.key for outcome in error.failed) == (requests[1],)
    assert error.first_failure is not None
    assert error.first_failure.key == requests[1]
    assert isinstance(error.first_failure.error, RuntimeError)
