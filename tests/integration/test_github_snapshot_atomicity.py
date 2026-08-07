"""Adversarial GitHub snapshot atomicity: no mixed A/B metadata+content."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase
from tests.integration.test_github_strict_full_diff import (
    BASE_TIP,
    FakeFile,
    HEAD,
    HEAD2,
    _build_stack,
    _standard_trees_blobs,
)

MERGE_BASE2 = "f" * 40


@pytest.mark.integration
@pytest.mark.anyio
async def test_stable_snapshot_succeeds() -> None:
    trees, blobs = _standard_trees_blobs()
    files = [FakeFile("a.py", "modified")]
    reader, cache, _api, repo = _build_stack(files=files, trees=trees, blobs=blobs)
    result = await GetPRDiffUseCase(reader, cache).execute("acme", "demo", 1)
    assert result is not None
    assert len(result.files) == 1
    assert cache.sets == 1
    assert all(c[0] == BASE_TIP and c[1] == HEAD for c in repo.compare_calls)


@pytest.mark.integration
@pytest.mark.anyio
async def test_head_mutation_at_revalidate_is_snapshot_changed() -> None:
    trees, blobs = _standard_trees_blobs()
    files = [FakeFile("a.py", "modified")]
    revalidate = SimpleNamespace(
        base=SimpleNamespace(sha=BASE_TIP),
        head=SimpleNamespace(sha=HEAD2),
        changed_files=1,
    )
    reader, cache, _api, _repo = _build_stack(
        files=files,
        trees=trees,
        blobs=blobs,
        revalidate_pr=revalidate,
    )
    with pytest.raises(FullDiffIncompleteError) as ei:
        await GetPRDiffUseCase(reader, cache).execute("acme", "demo", 2)
    assert ei.value.reason is FullDiffIncompleteReason.SNAPSHOT_CHANGED
    assert cache.sets == 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_count_mutation_at_revalidate_is_snapshot_changed() -> None:
    trees, blobs = _standard_trees_blobs()
    files = [FakeFile("a.py", "modified")]
    revalidate = SimpleNamespace(
        base=SimpleNamespace(sha=BASE_TIP),
        head=SimpleNamespace(sha=HEAD),
        changed_files=99,
    )
    reader, cache, _api, _repo = _build_stack(
        files=files,
        trees=trees,
        blobs=blobs,
        revalidate_pr=revalidate,
    )
    with pytest.raises(FullDiffIncompleteError) as ei:
        await GetPRDiffUseCase(reader, cache).execute("acme", "demo", 3)
    assert ei.value.reason is FullDiffIncompleteReason.SNAPSHOT_CHANGED
    assert cache.sets == 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_base_tip_only_change_remains_coherent() -> None:
    """Base tip can move if merge-base/head/count stay fixed — identity/content still A."""
    trees, blobs = _standard_trees_blobs()
    files = [FakeFile("a.py", "modified")]
    # Revalidate with a different tip but same head/count; compare still returns MERGE_BASE.
    revalidate = SimpleNamespace(
        base=SimpleNamespace(sha="9" * 40),
        head=SimpleNamespace(sha=HEAD),
        changed_files=1,
    )
    reader, cache, _api, _repo = _build_stack(
        files=files,
        trees=trees,
        blobs=blobs,
        revalidate_pr=revalidate,
    )
    result = await GetPRDiffUseCase(reader, cache).execute("acme", "demo", 4)
    assert result is not None
    assert result.files[0].path == "a.py"
    assert "changed" in result.files[0].diff or "line1" in result.files[0].diff
    assert cache.sets == 1
