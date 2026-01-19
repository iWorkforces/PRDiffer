"""Unit tests for RateLimiter application component.

Tests the RateLimiter component which provides per-client rate limiting
with configurable limits and sliding window tracking.
"""

import time
from unittest.mock import Mock
from prdiffer.application.components.rate_limiter import RateLimiter


class TestRateLimiterInitialization:
    """Test suite for RateLimiter initialization."""

    def test_rate_limiter_initialization(self):
        """Test RateLimiter can be initialized."""
        limiter = RateLimiter()

        assert limiter is not None
        assert hasattr(limiter, "_rate_limit_requests")
        assert hasattr(limiter, "_rate_limit_window")
        assert hasattr(limiter, "_client_timestamps")

    def test_rate_limiter_with_logger(self):
        """Test RateLimiter with custom logger."""
        mock_logger = Mock()
        limiter = RateLimiter(logger=mock_logger)

        assert limiter._logger == mock_logger

    def test_rate_limiter_default_values(self):
        """Test RateLimiter has correct default values."""
        limiter = RateLimiter()

        assert limiter._rate_limit_requests == 100
        assert limiter._rate_limit_window == 60
        assert limiter._cleanup_interval == 300
        assert limiter._client_ttl == 3600

    def test_rate_limiter_empty_state(self):
        """Test RateLimiter starts with empty state."""
        limiter = RateLimiter()

        assert limiter.get_active_clients_count() == 0
        assert len(limiter._client_timestamps) == 0
        assert len(limiter._last_access) == 0


class TestRateLimiterCheckRateLimit:
    """Test suite for check_rate_limit method."""

    def test_check_rate_limit_first_request_allowed(self):
        """Test that first request is always allowed."""
        limiter = RateLimiter()

        result = limiter.check_rate_limit("client1")

        assert result is True

    def test_check_rate_limit_under_limit(self):
        """Test that requests under the limit are allowed."""
        limiter = RateLimiter()

        # Make requests under the limit
        for _ in range(99):
            assert limiter.check_rate_limit("client1") is True

    def test_check_rate_limit_at_limit(self):
        """Test that request at the limit is rejected."""
        limiter = RateLimiter()

        # check_rate_limit doesn't increment - need to use increment_rate_limit
        for _ in range(100):
            limiter.increment_rate_limit("client1")

        # Now check should return False (at limit)
        result = limiter.check_rate_limit("client1")

        assert result is False

    def test_check_rate_limit_exceeds_limit(self):
        """Test that request exceeding the limit is rejected."""
        limiter = RateLimiter()

        # Make requests up to and beyond the limit
        for _ in range(101):
            limiter.increment_rate_limit("client1")

        # Should be rate limited now
        result = limiter.check_rate_limit("client1")

        assert result is False

    def test_check_rate_limit_multiple_clients(self):
        """Test rate limiting is per-client."""
        limiter = RateLimiter()

        # Client 1 uses up their limit
        for _ in range(100):
            limiter.increment_rate_limit("client1")

        # Client 1 should be rate limited
        assert limiter.check_rate_limit("client1") is False

        # Client 2 should still be allowed
        assert limiter.check_rate_limit("client2") is True

    def test_check_rate_limit_window_expiry(self):
        """Test that old requests outside window are not counted."""
        limiter = RateLimiter()

        # Use up the limit
        for _ in range(100):
            limiter.increment_rate_limit("client1")

        assert limiter.check_rate_limit("client1") is False

        # Set all timestamps to be outside the window
        current_time = time.time()
        limiter._client_timestamps["client1"] = [
            current_time - limiter._rate_limit_window - 1 for _ in range(100)
        ]

        # Now the request should be allowed since all old requests expired
        # check_rate_limit will clean up old timestamps
        assert limiter.check_rate_limit("client1") is True


class TestRateLimiterIncrement:
    """Test suite for increment_rate_limit method."""

    def test_increment_rate_limit(self):
        """Test incrementing rate limit counter."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")

        assert limiter.get_current_rate("client1") == 1

    def test_increment_rate_limit_multiple(self):
        """Test multiple increments."""
        limiter = RateLimiter()

        for i in range(5):
            limiter.increment_rate_limit("client1")

        assert limiter.get_current_rate("client1") == 5

    def test_increment_rate_limit_different_clients(self):
        """Test increments are per-client."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client2")

        assert limiter.get_current_rate("client1") == 1
        assert limiter.get_current_rate("client2") == 1


class TestRateLimiterGetCurrentRate:
    """Test suite for get_current_rate method."""

    def test_get_current_rate_new_client(self):
        """Test get_current_rate for new client returns 0."""
        limiter = RateLimiter()

        rate = limiter.get_current_rate("new_client")

        assert rate == 0

    def test_get_current_rate_after_increments(self):
        """Test get_current_rate reflects increments."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")

        assert limiter.get_current_rate("client1") == 3

    def test_get_current_rate_global(self):
        """Test get_current_rate with 'global' identifier returns max."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client2")

        global_rate = limiter.get_current_rate("global")

        # Should return the maximum across all clients
        assert global_rate == 2

    def test_get_current_rate_global_empty(self):
        """Test get_current_rate with 'global' when no clients returns 0."""
        limiter = RateLimiter()

        global_rate = limiter.get_current_rate("global")

        assert global_rate == 0


class TestRateLimiterGetRateLimitInfo:
    """Test suite for get_rate_limit_info method."""

    def test_get_rate_limit_info_structure(self):
        """Test get_rate_limit_info returns correct structure."""
        limiter = RateLimiter()

        info = limiter.get_rate_limit_info("client1")

        assert "max_requests" in info
        assert "window_seconds" in info
        assert "current_requests" in info
        assert "remaining_requests" in info
        assert "identifier" in info

    def test_get_rate_limit_info_values(self):
        """Test get_rate_limit_info returns correct values."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")

        info = limiter.get_rate_limit_info("client1")

        assert info["max_requests"] == 100
        assert info["window_seconds"] == 60
        assert info["current_requests"] == 2
        assert info["remaining_requests"] == 98
        assert info["identifier"] == "client1"

    def test_get_rate_limit_info_at_limit(self):
        """Test get_rate_limit_info when at limit."""
        limiter = RateLimiter()

        for _ in range(100):
            limiter.increment_rate_limit("client1")

        info = limiter.get_rate_limit_info("client1")

        assert info["current_requests"] == 100
        assert info["remaining_requests"] == 0


class TestRateLimiterResetClient:
    """Test suite for reset_client method."""

    def test_reset_client_existing(self):
        """Test resetting an existing client."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")
        limiter.check_rate_limit("client1")  # Populate _last_access

        result = limiter.reset_client("client1")

        assert result is True
        assert limiter.get_current_rate("client1") == 0

    def test_reset_client_nonexistent(self):
        """Test resetting a non-existent client returns False."""
        limiter = RateLimiter()

        result = limiter.reset_client("nonexistent")

        assert result is False

    def test_reset_client_removes_from_timestamps(self):
        """Test that reset_client removes client from timestamps."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.check_rate_limit("client1")  # Populate _last_access

        limiter.reset_client("client1")

        assert "client1" not in limiter._client_timestamps

    def test_reset_client_removes_from_last_access(self):
        """Test that reset_client removes client from last_access."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.check_rate_limit("client1")  # Populate _last_access

        limiter.reset_client("client1")

        assert "client1" not in limiter._last_access


class TestRateLimiterGetActiveClientsCount:
    """Test suite for get_active_clients_count method."""

    def test_get_active_clients_count_empty(self):
        """Test get_active_clients_count when no clients."""
        limiter = RateLimiter()

        count = limiter.get_active_clients_count()

        assert count == 0

    def test_get_active_clients_count_single_client(self):
        """Test get_active_clients_count with one client."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")

        count = limiter.get_active_clients_count()

        assert count == 1

    def test_get_active_clients_count_multiple_clients(self):
        """Test get_active_clients_count with multiple clients."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client2")
        limiter.increment_rate_limit("client3")

        count = limiter.get_active_clients_count()

        assert count == 3

    def test_get_active_clients_count_counts_unique(self):
        """Test get_active_clients_count counts unique clients."""
        limiter = RateLimiter()

        # Same client multiple times
        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")

        count = limiter.get_active_clients_count()

        assert count == 1


class TestRateLimiterGetAllClientInfo:
    """Test suite for get_all_client_info method."""

    def test_get_all_client_info_empty(self):
        """Test get_all_client_info when no clients."""
        limiter = RateLimiter()

        info = limiter.get_all_client_info()

        assert info == {}

    def test_get_all_client_info_structure(self):
        """Test get_all_client_info returns correct structure."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client2")

        info = limiter.get_all_client_info()

        assert "client1" in info
        assert "client2" in info

        # Check structure of client info
        for client_info in info.values():
            assert "current_requests" in client_info
            assert "max_requests" in client_info
            assert "remaining_requests" in client_info
            assert "last_access" in client_info

    def test_get_all_client_info_values(self):
        """Test get_all_client_info returns correct values."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("client1")
        limiter.increment_rate_limit("client1")

        info = limiter.get_all_client_info()

        assert info["client1"]["current_requests"] == 2
        assert info["client1"]["max_requests"] == 100
        assert info["client1"]["remaining_requests"] == 98


class TestRateLimiterCleanup:
    """Test suite for automatic cleanup functionality."""

    def test_expired_clients_removed(self):
        """Test that expired clients are removed during cleanup."""
        limiter = RateLimiter()

        # Simulate a client with old timestamps
        current_time = time.time()
        limiter._client_timestamps["old_client"] = [
            current_time - limiter._client_ttl - 1
        ]
        limiter._last_access["old_client"] = current_time - limiter._client_ttl - 1

        # Manually trigger cleanup
        limiter._cleanup_old_entries(current_time)

        # Old client should be removed
        assert "old_client" not in limiter._client_timestamps
        assert "old_client" not in limiter._last_access

    def test_active_clients_preserved(self):
        """Test that active clients are preserved during cleanup."""
        limiter = RateLimiter()

        limiter.increment_rate_limit("active_client")

        # Set last access to recent time
        current_time = time.time()
        limiter._last_access["active_client"] = current_time

        # Add an old client to trigger cleanup
        limiter._client_timestamps["old_client"] = [
            current_time - limiter._client_ttl - 1
        ]
        limiter._last_access["old_client"] = current_time - limiter._client_ttl - 1

        # Manually trigger cleanup
        limiter._cleanup_old_entries(current_time)

        # Active client should still be present
        assert "active_client" in limiter._client_timestamps
        assert "active_client" in limiter._last_access


class TestRateLimiterEdgeCases:
    """Test suite for RateLimiter edge cases."""

    def test_empty_identifier(self):
        """Test RateLimiter with empty identifier."""
        limiter = RateLimiter()

        # Empty string identifier should work
        result = limiter.check_rate_limit("")

        assert result is True

    def test_special_characters_in_identifier(self):
        """Test RateLimiter with special characters in identifier."""
        limiter = RateLimiter()

        special_ids = [
            "client-with-dash",
            "client_with_underscore",
            "client.with.dots",
            "client@domain",
        ]

        for identifier in special_ids:
            result = limiter.check_rate_limit(identifier)
            assert result is True

    def test_very_long_identifier(self):
        """Test RateLimiter with very long identifier."""
        limiter = RateLimiter()

        long_id = "x" * 1000

        result = limiter.check_rate_limit(long_id)

        assert result is True

    def test_unicode_identifier(self):
        """Test RateLimiter with unicode identifier."""
        limiter = RateLimiter()

        unicode_id = "client-测试-🚀"

        result = limiter.check_rate_limit(unicode_id)

        assert result is True

    def test_concurrent_clients(self):
        """Test RateLimiter handles multiple concurrent clients."""
        limiter = RateLimiter()

        # Create many clients
        num_clients = 50
        for i in range(num_clients):
            identifier = f"client{i}"
            limiter.increment_rate_limit(identifier)

        # Each client should have their own count
        for i in range(num_clients):
            identifier = f"client{i}"
            assert limiter.get_current_rate(identifier) == 1

        assert limiter.get_active_clients_count() == num_clients


class TestRateLimiterProtocolCompliance:
    """Test suite for RateLimiter protocol compliance."""

    def test_implements_protocol(self):
        """Test that RateLimiter has all required protocol methods.
        Note: isinstance() requires @runtime_checkable decorator on Protocol.
        This test verifies the class has all required methods (duck typing).
        """

        limiter = RateLimiter()

        # Check that all protocol methods exist and are callable
        protocol_methods = [
            "check_rate_limit",
            "increment_rate_limit",
        ]

        for method_name in protocol_methods:
            assert hasattr(limiter, method_name)
            assert callable(getattr(limiter, method_name))

    def test_has_required_methods(self):
        """Test that RateLimiter has all required protocol methods."""
        limiter = RateLimiter()

        # Check all required methods exist
        assert hasattr(limiter, "check_rate_limit")
        assert callable(limiter.check_rate_limit)
        assert hasattr(limiter, "increment_rate_limit")
        assert callable(limiter.increment_rate_limit)
        assert hasattr(limiter, "get_current_rate")
        assert callable(limiter.get_current_rate)
        assert hasattr(limiter, "get_rate_limit_info")
        assert callable(limiter.get_rate_limit_info)
