"""Tests for RepositoryCacheService."""

import time
from unittest.mock import MagicMock, patch

import pytest

from prdiffer.infrastructure.cache.cache_repository import (
    RepositoryCacheService,
    get_repository_cache_service,
)


def _make_repo_mock(owner: str = "acme", name: str = "widgets", pr: int = 42) -> MagicMock:
    """Create a mock PRDiffRepositoryInterface."""
    mock = MagicMock()
    mock.repo_owner = owner
    mock.repo_name = name
    mock.pr_number = pr
    mock._initialized = True
    return mock


@pytest.mark.unit
class TestRepositoryCacheServiceInsertRetrieve:
    """Test basic insert / retrieve flow."""

    def test_insert_returns_true(self):
        svc = RepositoryCacheService()
        repo = _make_repo_mock()
        assert svc.insert(repo) is True

    def test_retrieve_returns_inserted_repo(self):
        svc = RepositoryCacheService()
        repo = _make_repo_mock()
        svc.insert(repo)
        result = svc.retrieve("acme", "widgets", 42)
        assert result is repo

    def test_retrieve_missing_returns_none(self):
        svc = RepositoryCacheService()
        assert svc.retrieve("no", "such", 1) is None

    def test_retrieve_case_insensitive(self):
        svc = RepositoryCacheService()
        repo = _make_repo_mock(owner="Acme", name="Widgets")
        svc.insert(repo)
        result = svc.retrieve("acme", "widgets", 42)
        assert result is repo

    def test_insert_overwrites_same_key(self):
        svc = RepositoryCacheService()
        repo1 = _make_repo_mock()
        repo2 = _make_repo_mock()
        svc.insert(repo1)
        svc.insert(repo2)
        result = svc.retrieve("acme", "widgets", 42)
        assert result is repo2


@pytest.mark.unit
class TestRepositoryCacheServiceValidate:
    """Test validate method."""

    def test_validate_existing_entry(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock())
        assert svc.validate("acme", "widgets", 42) is True

    def test_validate_missing_entry(self):
        svc = RepositoryCacheService()
        assert svc.validate("no", "such", 1) is False


@pytest.mark.unit
class TestRepositoryCacheServiceRemove:
    """Test remove method."""

    def test_remove_existing_returns_true(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock())
        assert svc.remove("acme", "widgets", 42) is True

    def test_remove_missing_returns_false(self):
        svc = RepositoryCacheService()
        assert svc.remove("no", "such", 1) is False

    def test_remove_makes_retrieve_return_none(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock())
        svc.remove("acme", "widgets", 42)
        assert svc.retrieve("acme", "widgets", 42) is None


@pytest.mark.unit
class TestRepositoryCacheServiceClearAndSize:
    """Test clear and size methods."""

    def test_size_empty(self):
        svc = RepositoryCacheService()
        assert svc.size() == 0

    def test_size_after_inserts(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock(pr=1))
        svc.insert(_make_repo_mock(pr=2))
        assert svc.size() == 2

    def test_clear_empties_cache(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock(pr=1))
        svc.insert(_make_repo_mock(pr=2))
        svc.clear()
        assert svc.size() == 0


@pytest.mark.unit
class TestRepositoryCacheServiceTTL:
    """Test TTL expiry behaviour."""

    def test_expired_entry_not_retrieved(self):
        svc = RepositoryCacheService(ttl_seconds=1)
        svc.insert(_make_repo_mock())
        # Patch time to simulate expiry
        with patch("prdiffer.infrastructure.cache.cache_repository.time") as mock_time:
            # Insert happened at real time; fake "now" far in the future
            mock_time.time.return_value = time.time() + 100
            result = svc.retrieve("acme", "widgets", 42)
        assert result is None

    def test_expired_entry_not_validated(self):
        svc = RepositoryCacheService(ttl_seconds=1)
        svc.insert(_make_repo_mock())
        with patch("prdiffer.infrastructure.cache.cache_repository.time") as mock_time:
            mock_time.time.return_value = time.time() + 100
            assert svc.validate("acme", "widgets", 42) is False


@pytest.mark.unit
class TestRepositoryCacheServiceEviction:
    """Test LRU eviction when max_size exceeded."""

    def test_eviction_removes_oldest(self):
        svc = RepositoryCacheService(max_size=2)
        repo1 = _make_repo_mock(pr=1)
        repo2 = _make_repo_mock(pr=2)
        repo3 = _make_repo_mock(pr=3)

        svc.insert(repo1)
        svc.insert(repo2)
        # This insert triggers eviction — repo1 (oldest) should be evicted
        svc.insert(repo3)

        # After eviction, size should be <= max_size
        assert svc.size() <= 3  # eviction happens on insert
        assert svc.retrieve("acme", "widgets", 3) is repo3

    def test_eviction_keeps_max_size_entries(self):
        svc = RepositoryCacheService(max_size=2)
        for i in range(5):
            svc.insert(_make_repo_mock(pr=i))
        assert svc.size() <= 3  # max_size + 1 before eviction


@pytest.mark.unit
class TestRepositoryCacheServiceStats:
    """Test stats method."""

    def test_stats_empty_cache(self):
        svc = RepositoryCacheService(max_size=50, ttl_seconds=300)
        stats = svc.stats()
        assert stats["total_entries"] == 0
        assert stats["initialized_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["max_size"] == 50
        assert stats["ttl_seconds"] == 300

    def test_stats_with_entries(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock(pr=1))
        svc.insert(_make_repo_mock(pr=2))
        stats = svc.stats()
        assert stats["total_entries"] == 2
        assert stats["initialized_entries"] == 2

    def test_stats_counts_uninitialized(self):
        svc = RepositoryCacheService()
        repo = _make_repo_mock()
        repo._initialized = False
        svc.insert(repo)
        stats = svc.stats()
        assert stats["total_entries"] == 1
        assert stats["initialized_entries"] == 0


@pytest.mark.unit
class TestRepositoryCacheServiceInvalidate:
    """Test invalidate method with string cache keys."""

    def test_invalidate_owner_repo_format(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock(owner="acme", name="widgets", pr=0))
        result = svc.invalidate("acme/widgets")
        assert result is True

    def test_invalidate_owner_repo_pr_format(self):
        svc = RepositoryCacheService()
        svc.insert(_make_repo_mock(owner="acme", name="widgets", pr=42))
        result = svc.invalidate("acme/widgets/pr/42")
        assert result is True

    def test_invalidate_bad_format_returns_false(self):
        svc = RepositoryCacheService()
        assert svc.invalidate("bad") is False
        assert svc.invalidate("a/b/c") is False
        assert svc.invalidate("") is False

    def test_invalidate_bad_pr_number_returns_false(self):
        svc = RepositoryCacheService()
        assert svc.invalidate("acme/widgets/pr/abc") is False


@pytest.mark.unit
class TestGetRepositoryCacheServiceSingleton:
    """Test module-level singleton factory."""

    def test_returns_instance(self):
        import prdiffer.infrastructure.cache.cache_repository as mod

        old = mod._repository_cache_service
        mod._repository_cache_service = None
        try:
            result = get_repository_cache_service()
            assert isinstance(result, RepositoryCacheService)
        finally:
            mod._repository_cache_service = old

    def test_returns_same_instance(self):
        import prdiffer.infrastructure.cache.cache_repository as mod

        old = mod._repository_cache_service
        mod._repository_cache_service = None
        try:
            r1 = get_repository_cache_service()
            r2 = get_repository_cache_service()
            assert r1 is r2
        finally:
            mod._repository_cache_service = old
