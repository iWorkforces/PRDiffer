"""Tests for CacheKeyManager key generation and hashing."""

import pytest

from prdiffer.infrastructure.cache.keys import CacheKeyManager
from prdiffer.domain.exceptions import ValidationError


@pytest.mark.unit
class TestCacheKeyManagerInit:
    """Tests for CacheKeyManager initialization."""

    def test_default_init(self):
        """Default init uses md5 hashing with key mapping."""
        manager = CacheKeyManager()
        assert manager.use_hashed_keys is True
        assert manager.hash_algorithm == "md5"

    def test_custom_init(self):
        """Custom init stores provided values."""
        manager = CacheKeyManager(
            use_hashed_keys=False,
            hash_algorithm="sha256",
            store_key_mapping=False,
        )
        assert manager.use_hashed_keys is False
        assert manager.hash_algorithm == "sha256"

    def test_hashing_disabled(self):
        """Hashing can be disabled."""
        manager = CacheKeyManager(use_hashed_keys=False)
        assert manager.use_hashed_keys is False


@pytest.mark.unit
class TestGenerateKey:
    """Tests for generate_key method."""

    def test_basic_key_format(self):
        """Key follows owner/repo/pr/number format."""
        manager = CacheKeyManager()
        key = manager.generate_key("owner", "repo", 123)
        assert key == "owner/repo/pr/123"

    def test_hyphenated_names(self):
        """Hyphenated owner/repo names are preserved."""
        manager = CacheKeyManager()
        key = manager.generate_key("my-org", "my-repo", 456)
        assert key == "my-org/my-repo/pr/456"

    def test_dotted_names(self):
        """Dotted repo names are preserved."""
        manager = CacheKeyManager()
        key = manager.generate_key("owner", "repo.name", 789)
        assert key == "owner/repo.name/pr/789"

    def test_pr_number_zero(self):
        """PR number 0 is valid."""
        manager = CacheKeyManager()
        key = manager.generate_key("owner", "repo", 0)
        assert key == "owner/repo/pr/0"

    def test_large_pr_number(self):
        """Large PR numbers are supported."""
        manager = CacheKeyManager()
        key = manager.generate_key("owner", "repo", 99999)
        assert key == "owner/repo/pr/99999"


@pytest.mark.unit
class TestHashKey:
    """Tests for hash_key method."""

    def test_md5_hash_length(self):
        """MD5 produces 32 character hex digest."""
        manager = CacheKeyManager(hash_algorithm="md5")
        hashed = manager.hash_key("test_key")
        assert len(hashed) == 32
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_sha256_hash_length(self):
        """SHA256 produces 64 character hex digest."""
        manager = CacheKeyManager(hash_algorithm="sha256")
        hashed = manager.hash_key("test_key")
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_sha256_short_hash_length(self):
        """SHA256 short produces 16 character hex digest."""
        manager = CacheKeyManager(hash_algorithm="sha256_short")
        hashed = manager.hash_key("test_key")
        assert len(hashed) == 16

    def test_unsupported_algorithm_raises(self):
        """Unsupported hash algorithm raises ValidationError."""
        manager = CacheKeyManager(hash_algorithm="invalid")
        with pytest.raises(ValidationError, match="Unsupported hash algorithm"):
            manager.hash_key("test_key")

    def test_hash_consistency(self):
        """Same input always produces same hash."""
        manager = CacheKeyManager(hash_algorithm="md5")
        hash1 = manager.hash_key("owner/repo/pr/123")
        hash2 = manager.hash_key("owner/repo/pr/123")
        assert hash1 == hash2

    def test_hash_different_inputs(self):
        """Different inputs produce different hashes."""
        manager = CacheKeyManager(hash_algorithm="md5")
        hash1 = manager.hash_key("key1")
        hash2 = manager.hash_key("key2")
        assert hash1 != hash2

    def test_hash_empty_string(self):
        """Empty string produces valid hash."""
        manager = CacheKeyManager(hash_algorithm="md5")
        hashed = manager.hash_key("")
        assert len(hashed) == 32

    def test_hash_unicode_key(self):
        """Unicode keys produce valid hash."""
        manager = CacheKeyManager(hash_algorithm="md5")
        hashed = manager.hash_key("日本語/リポ/pr/123")
        assert len(hashed) == 32


@pytest.mark.unit
class TestGetInternalKey:
    """Tests for get_internal_key method."""

    def test_hashing_enabled(self):
        """With hashing enabled, returns hashed key and display."""
        manager = CacheKeyManager(use_hashed_keys=True, hash_algorithm="md5")
        internal_key, display = manager.get_internal_key("owner/repo/pr/123")
        assert len(internal_key) == 32
        assert display == f"{internal_key[:8]}..."

    def test_hashing_disabled(self):
        """With hashing disabled, returns original key and empty display."""
        manager = CacheKeyManager(use_hashed_keys=False)
        internal_key, display = manager.get_internal_key("owner/repo/pr/123")
        assert internal_key == "owner/repo/pr/123"
        assert display == ""

    def test_display_format(self):
        """Display shows first 8 chars of hash with ellipsis."""
        manager = CacheKeyManager(use_hashed_keys=True, hash_algorithm="sha256")
        internal_key, display = manager.get_internal_key("test")
        assert display.endswith("...")
        assert len(display) == 11  # 8 chars + '...'


@pytest.mark.unit
class TestCacheKeyCollisions:
    """Tests for cache key collision avoidance."""

    def test_different_owners_different_keys(self):
        """Different owners produce different keys."""
        manager = CacheKeyManager()
        key1 = manager.generate_key("owner1", "repo", 1)
        key2 = manager.generate_key("owner2", "repo", 1)
        assert key1 != key2
        assert manager.hash_key(key1) != manager.hash_key(key2)

    def test_different_repos_different_keys(self):
        """Different repos produce different keys."""
        manager = CacheKeyManager()
        key1 = manager.generate_key("owner", "repo1", 1)
        key2 = manager.generate_key("owner", "repo2", 1)
        assert key1 != key2

    def test_different_prs_different_keys(self):
        """Different PR numbers produce different keys."""
        manager = CacheKeyManager()
        key1 = manager.generate_key("owner", "repo", 1)
        key2 = manager.generate_key("owner", "repo", 2)
        assert key1 != key2
