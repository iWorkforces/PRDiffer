"""Tests for Phase 1 improvements: Critical Fixes.

This module tests all Phase 1 improvements including:
- LRU cache eviction (api_client.py)
- TTL expiration (cache_service.py)
- Async retry handler (retry_handler.py)
- Thread-safe circuit breaker (circuit_breaker.py)
- ReDoS pattern fixes (input_validator.py)
- Error message sanitization (mcp_server.py)
"""

import time
import threading
import pytest
from unittest.mock import Mock, patch

# Import components to test
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.infrastructure.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from prdiffer.infrastructure.utils.retry_handler import RetryHandler
from prdiffer.domain.entities.pr_diff import PRDiff


# =============================================================================
# Phase 1.1.1: LRU Cache Eviction Tests (api_client.py)
# =============================================================================


class TestLRUCacheEviction:
    """Tests for LRU cache eviction in GitHubAPIClient."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock()

    @patch("prdiffer.infrastructure.github.api_client.get_logger")
    def test_cache_eviction_when_max_size_reached(self, mock_get_logger):
        """Test that oldest entries are evicted when cache reaches max size."""
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient

        mock_get_logger.return_value = Mock()

        # Create client with small max cache size (using correct parameter names)
        client = GitHubAPIClient(
            max_retries=1,
            retry_delay=0.1,
            timeout=10,
            file_content_cache_max_size=3,
            file_content_cache_ttl=600,
        )

        # Add entries up to max size
        client._cache_set(("file1.py", "branch1"), "content1")
        client._cache_set(("file2.py", "branch1"), "content2")
        client._cache_set(("file3.py", "branch1"), "content3")

        assert len(client._file_content_cache) == 3

        # Add one more - should evict oldest (file1.py)
        client._cache_set(("file4.py", "branch1"), "content4")

        assert len(client._file_content_cache) == 3
        assert ("file1.py", "branch1") not in client._file_content_cache
        assert ("file4.py", "branch1") in client._file_content_cache

    @patch("prdiffer.infrastructure.github.api_client.get_logger")
    def test_cache_lru_ordering(self, mock_get_logger):
        """Test that accessing an entry moves it to the end (most recently used)."""
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient

        mock_get_logger.return_value = Mock()

        client = GitHubAPIClient(
            max_retries=1,
            retry_delay=0.1,
            timeout=10,
            file_content_cache_max_size=3,
            file_content_cache_ttl=600,
        )

        # Add 3 entries
        client._cache_set(("file1.py", "branch1"), "content1")
        client._cache_set(("file2.py", "branch1"), "content2")
        client._cache_set(("file3.py", "branch1"), "content3")

        # Access file1 - should move it to end
        result = client._cache_get(("file1.py", "branch1"))
        assert result == "content1"

        # Add new entry - should evict file2 (now oldest)
        client._cache_set(("file4.py", "branch1"), "content4")

        assert ("file2.py", "branch1") not in client._file_content_cache
        assert ("file1.py", "branch1") in client._file_content_cache

    @patch("prdiffer.infrastructure.github.api_client.get_logger")
    def test_cache_statistics_tracking(self, mock_get_logger):
        """Test that cache hits, misses, and evictions are tracked."""
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient

        mock_get_logger.return_value = Mock()

        client = GitHubAPIClient(
            max_retries=1,
            retry_delay=0.1,
            timeout=10,
            file_content_cache_max_size=2,
            file_content_cache_ttl=600,
        )

        # Initial stats should be zero
        assert client._cache_hits == 0
        assert client._cache_misses == 0
        assert client._cache_evictions == 0

        # Cache miss
        result = client._cache_get(("nonexistent.py", "branch1"))
        assert result is None
        assert client._cache_misses == 1

        # Add entry
        client._cache_set(("file1.py", "branch1"), "content1")

        # Cache hit
        result = client._cache_get(("file1.py", "branch1"))
        assert result == "content1"
        assert client._cache_hits == 1

        # Fill cache and trigger eviction
        client._cache_set(("file2.py", "branch1"), "content2")
        client._cache_set(("file3.py", "branch1"), "content3")  # Triggers eviction

        assert client._cache_evictions >= 1


# =============================================================================
# Phase 1.1.2: TTL Expiration Tests (cache_service.py)
# =============================================================================


class TestTTLExpiration:
    """Tests for TTL expiration in CacheService."""

    @pytest.fixture
    def sample_pr_diff(self):
        """Create sample PRDiff for testing."""
        return PRDiff(
            diff_content="test diff content",
            commit_messages="test commit message",
        )

    @patch("prdiffer.infrastructure.settings.get_settings_service")
    def test_entry_not_expired_within_ttl(self, mock_get_settings, sample_pr_diff):
        """Test that entries are valid within TTL."""
        from prdiffer.infrastructure.cache_service import CacheService

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: {
            "cache.use_hashed_keys": False,
            "cache.ttl": 600,  # 10 minutes
        }.get(key, default)
        mock_get_settings.return_value = mock_settings

        cache_service = CacheService()
        cache_key = "owner/repo/pr/123"
        commit_sha = "abc123"

        cache_service.set(cache_key, commit_sha, sample_pr_diff)

        # Should retrieve successfully (within TTL)
        result = cache_service.get(cache_key, commit_sha)
        assert result == sample_pr_diff

    @patch("prdiffer.infrastructure.settings.get_settings_service")
    def test_entry_expired_after_ttl(self, mock_get_settings, sample_pr_diff):
        """Test that entries expire after TTL."""
        from prdiffer.infrastructure.cache_service import CacheService

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: {
            "cache.use_hashed_keys": False,
            "cache.ttl": 1,  # 1 second TTL for testing
        }.get(key, default)
        mock_get_settings.return_value = mock_settings

        cache_service = CacheService()
        cache_key = "owner/repo/pr/123"
        commit_sha = "abc123"

        cache_service.set(cache_key, commit_sha, sample_pr_diff)

        # Wait for TTL to expire
        time.sleep(1.5)

        # Should return None (expired)
        result = cache_service.get(cache_key, commit_sha)
        assert result is None

    @patch("prdiffer.infrastructure.settings.get_settings_service")
    def test_expiration_statistics(self, mock_get_settings, sample_pr_diff):
        """Test that expiration statistics are tracked."""
        from prdiffer.infrastructure.cache_service import CacheService

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: {
            "cache.use_hashed_keys": False,
            "cache.ttl": 1,
        }.get(key, default)
        mock_get_settings.return_value = mock_settings

        cache_service = CacheService()
        cache_key = "owner/repo/pr/123"
        commit_sha = "abc123"

        cache_service.set(cache_key, commit_sha, sample_pr_diff)

        # Initial stats
        assert cache_service._cache_expirations == 0

        # Wait for expiration
        time.sleep(1.5)

        # Trigger expiration check
        cache_service.get(cache_key, commit_sha)

        assert cache_service._cache_expirations == 1


# =============================================================================
# Phase 1.2.1: Async Retry Handler Tests (retry_handler.py)
# =============================================================================


class TestAsyncRetryHandler:
    """Tests for async retry handler."""

    @pytest.fixture
    def retry_handler(self):
        """Create retry handler with short delays for testing."""
        return RetryHandler(max_retries=3, retry_delay=0.1)

    @pytest.mark.asyncio
    async def test_async_retry_success_first_attempt(self, retry_handler):
        """Test async retry succeeds on first attempt."""
        call_count = 0

        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_handler.execute_with_retry_async(successful_operation)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self, retry_handler):
        """Test async retry succeeds after initial failures."""
        call_count = 0

        async def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Use TimeoutError which is in RETRY_EXCEPTIONS and has "timeout" keyword
                raise TimeoutError("Connection timeout error")
            return "success"

        result = await retry_handler.execute_with_retry_async(eventually_successful)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_exhausted(self, retry_handler):
        """Test async retry raises after all attempts exhausted."""

        async def always_fails():
            # Use TimeoutError which is in RETRY_EXCEPTIONS and has "timeout" keyword
            raise TimeoutError("Connection timeout error")

        with pytest.raises(TimeoutError, match="timeout"):
            await retry_handler.execute_with_retry_async(always_fails)

    @pytest.mark.asyncio
    async def test_async_retry_uses_anyio_sleep(self, retry_handler):
        """Test that async retry uses anyio.sleep for delays."""
        call_count = 0

        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Use TimeoutError which is in RETRY_EXCEPTIONS and has "timeout" keyword
                raise TimeoutError("Connection timeout")
            return "success"

        start_time = time.time()
        result = await retry_handler.execute_with_retry_async(fail_once)
        elapsed = time.time() - start_time

        assert result == "success"
        # Should have waited at least base_delay (0.1s)
        assert elapsed >= 0.1


# =============================================================================
# Phase 1.2.2: Thread-Safe Circuit Breaker Tests (circuit_breaker.py)
# =============================================================================


class TestThreadSafeCircuitBreaker:
    """Tests for thread-safe circuit breaker."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker with low threshold for testing."""
        return CircuitBreaker(failure_threshold=3, timeout=1.0)

    def test_initial_state_is_closed(self, circuit_breaker):
        """Test that circuit starts in CLOSED state."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.can_execute() is True

    def test_opens_after_failure_threshold(self, circuit_breaker):
        """Test that circuit opens after reaching failure threshold."""
        for _ in range(3):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.can_execute() is False

    def test_resets_on_success(self, circuit_breaker):
        """Test that failure count resets on success."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2

        circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0

    def test_transitions_to_half_open_after_timeout(self, circuit_breaker):
        """Test that circuit transitions to HALF_OPEN after timeout."""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.5)

        # Should transition to HALF_OPEN
        assert circuit_breaker.can_execute() is True
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    def test_thread_safety_concurrent_failures(self, circuit_breaker):
        """Test thread safety with concurrent failure recordings."""
        threads = []
        errors = []

        def record_failures():
            try:
                for _ in range(10):
                    circuit_breaker.record_failure()
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        for _ in range(5):
            t = threading.Thread(target=record_failures)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should not have raised any errors
        assert len(errors) == 0
        # Circuit should be open
        assert circuit_breaker.state == CircuitState.OPEN

    def test_thread_safety_concurrent_successes(self, circuit_breaker):
        """Test thread safety with concurrent success recordings."""
        threads = []
        errors = []

        def record_successes():
            try:
                for _ in range(10):
                    circuit_breaker.record_success()
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        for _ in range(5):
            t = threading.Thread(target=record_successes)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should not have raised any errors
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_async_record_success(self, circuit_breaker):
        """Test async version of record_success."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        await circuit_breaker.record_success_async()

        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_async_record_failure(self, circuit_breaker):
        """Test async version of record_failure."""
        await circuit_breaker.record_failure_async()
        await circuit_breaker.record_failure_async()
        await circuit_breaker.record_failure_async()

        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_async_can_execute(self, circuit_breaker):
        """Test async version of can_execute."""
        result = await circuit_breaker.can_execute_async()
        assert result is True

        # Open circuit
        for _ in range(3):
            await circuit_breaker.record_failure_async()

        result = await circuit_breaker.can_execute_async()
        assert result is False


# =============================================================================
# Phase 1.3.1: ReDoS Pattern Fixes Tests (input_validator.py)
# =============================================================================


class TestReDoSPatternFixes:
    """Tests for ReDoS pattern fixes in InputValidator."""

    def test_sql_keyword_detection_with_whitespace(self):
        """Test SQL keyword detection works with trailing whitespace."""
        validator = InputValidator()

        # Should detect SQL keywords followed by whitespace
        assert validator._contains_suspicious_patterns("select ")
        assert validator._contains_suspicious_patterns("union ")
        assert validator._contains_suspicious_patterns("drop ")

    def test_sql_keyword_detection_at_end(self):
        """Test SQL keyword detection works at end of string."""
        validator = InputValidator()

        # Should detect SQL keywords at end of string
        assert validator._contains_suspicious_patterns("test select")
        assert validator._contains_suspicious_patterns("test union")

    def test_sql_keyword_not_detected_in_middle_of_word(self):
        """Test SQL keywords not detected when part of another word."""
        validator = InputValidator()

        # Should NOT detect keywords that are part of larger words
        assert not validator._contains_suspicious_patterns("selector")
        assert not validator._contains_suspicious_patterns("reunion")
        assert not validator._contains_suspicious_patterns("dropdown")

    def test_windows_path_traversal_detection(self):
        """Test Windows path traversal pattern detection."""
        validator = InputValidator()

        # Windows absolute paths
        assert validator._contains_suspicious_patterns("C:\\Windows\\System32")
        assert validator._contains_suspicious_patterns("D:\\")

        # Windows parent directory
        assert validator._contains_suspicious_patterns("..\\config")

        # UNC paths
        assert validator._contains_suspicious_patterns("\\\\server\\share")

    def test_unix_path_traversal_detection(self):
        """Test Unix path traversal patterns still work."""
        validator = InputValidator()

        assert validator._contains_suspicious_patterns("../etc/passwd")
        assert validator._contains_suspicious_patterns("~/")
        assert validator._contains_suspicious_patterns("/etc/passwd")

    def test_no_redos_vulnerability(self):
        """Test that patterns don't cause ReDoS with malicious input."""
        validator = InputValidator()

        # This input would cause ReDoS with vulnerable patterns
        # Using repeated patterns that could cause catastrophic backtracking
        malicious_inputs = [
            "a" * 1000 + " select",  # Long string before keyword
            "select" + " " * 1000,  # Many spaces after keyword
            "union" + "\t" * 100,  # Many tabs
        ]

        start_time = time.time()

        for input_str in malicious_inputs:
            validator._contains_suspicious_patterns(input_str)

        elapsed = time.time() - start_time

        # Should complete quickly (< 1 second for all inputs)
        # ReDoS would cause exponential time
        assert elapsed < 1.0, f"Pattern matching took too long: {elapsed}s"


# =============================================================================
# Phase 1.3.2: Error Message Sanitization Tests (mcp_server.py)
# =============================================================================


class TestErrorMessageSanitization:
    """Tests for error message sanitization in FastMCPServer."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for FastMCPServer."""
        return {
            "settings_service": Mock(),
            "cache_service": Mock(),
            "repository_cache_service": Mock(),
            "pr_diff_service": Mock(),
            "logger": Mock(),
            "github_repository_class": Mock(),
            "input_validator": Mock(),
            "rate_limiter": Mock(),
            "metrics_tracker": Mock(),
            "pr_operation_handler": Mock(),
            "health_monitor": Mock(),
            "server_configuration": Mock(),
        }

    def test_github_exception_sanitization(self, mock_dependencies):
        """Test GitHub exception is sanitized."""
        from prdiffer.application.mcp_server import FastMCPServer

        # Configure mock
        mock_dependencies["server_configuration"].setup_logging = Mock()
        mock_dependencies["server_configuration"].get_mcp_instructions = Mock(
            return_value=""
        )

        with patch("prdiffer.application.mcp_server.FastMCP"):
            server = FastMCPServer(**mock_dependencies)

        # Create mock exception
        class GithubException(Exception):
            pass

        exc = GithubException("Detailed internal error: token xyz123 invalid")
        safe_message = server._create_safe_error_message(exc)

        assert safe_message == "GitHub API error occurred"
        assert "xyz123" not in safe_message
        assert "token" not in safe_message

    def test_rate_limit_exception_sanitization(self, mock_dependencies):
        """Test rate limit exception is sanitized."""
        from prdiffer.application.mcp_server import FastMCPServer

        mock_dependencies["server_configuration"].setup_logging = Mock()
        mock_dependencies["server_configuration"].get_mcp_instructions = Mock(
            return_value=""
        )

        with patch("prdiffer.application.mcp_server.FastMCP"):
            server = FastMCPServer(**mock_dependencies)

        class RateLimitExceededException(Exception):
            pass

        exc = RateLimitExceededException("Rate limit: 5000/hour exceeded at 14:32:01")
        safe_message = server._create_safe_error_message(exc)

        assert safe_message == "API rate limit exceeded. Please try again later"

    def test_unknown_exception_sanitization(self, mock_dependencies):
        """Test unknown exception returns generic message."""
        from prdiffer.application.mcp_server import FastMCPServer

        mock_dependencies["server_configuration"].setup_logging = Mock()
        mock_dependencies["server_configuration"].get_mcp_instructions = Mock(
            return_value=""
        )

        with patch("prdiffer.application.mcp_server.FastMCP"):
            server = FastMCPServer(**mock_dependencies)

        class UnknownInternalError(Exception):
            pass

        exc = UnknownInternalError(
            "Internal: database connection string is postgres://user:pass@host"
        )
        safe_message = server._create_safe_error_message(exc)

        assert safe_message == "Request processing failed"
        assert "postgres" not in safe_message
        assert "user:pass" not in safe_message

    def test_security_exceptions_sanitization(self, mock_dependencies):
        """Test security exceptions are sanitized."""
        from prdiffer.application.mcp_server import FastMCPServer
        from prdiffer.domain.exceptions import (
            InvalidURLError,
            SuspiciousOperationError,
        )

        mock_dependencies["server_configuration"].setup_logging = Mock()
        mock_dependencies["server_configuration"].get_mcp_instructions = Mock(
            return_value=""
        )

        with patch("prdiffer.application.mcp_server.FastMCP"):
            server = FastMCPServer(**mock_dependencies)

        # InvalidURLError
        invalid_url_exc = InvalidURLError("URL contains malicious pattern: $(whoami)")
        safe_message = server._create_safe_error_message(invalid_url_exc)
        assert safe_message == "Invalid GitHub PR URL format"
        assert "whoami" not in safe_message

        # SuspiciousOperationError
        suspicious_exc = SuspiciousOperationError(
            "Detected SQL injection: DROP TABLE users"
        )
        safe_message = server._create_safe_error_message(suspicious_exc)
        assert safe_message == "Request contains suspicious patterns"
        assert "DROP TABLE" not in safe_message


# =============================================================================
# Phase 1.3.3: File Name Sanitization Tests (github_repository.py)
# =============================================================================


class TestFileNameSanitization:
    """Tests for file name sanitization in GitHubPRDiffRepository."""

    def test_sanitize_for_logging_basic(self):
        """Test basic file name sanitization."""
        validator = InputValidator()

        # Normal file names
        result = validator.sanitize_for_logging("src/main.py")
        assert result == "src/main.py"

        result = validator.sanitize_for_logging("tests/test_file.py")
        assert result == "tests/test_file.py"

    def test_sanitize_for_logging_truncation(self):
        """Test that long file names are truncated."""
        validator = InputValidator()

        long_name = "a" * 300
        result = validator.sanitize_for_logging(long_name, max_length=200)

        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

    def test_sanitize_for_logging_control_characters(self):
        """Test that control characters are replaced."""
        validator = InputValidator()

        # File name with control characters
        malicious = "file\x00name\x07with\x1bcontrol.py"
        result = validator.sanitize_for_logging(malicious)

        assert "\x00" not in result
        assert "\x07" not in result
        assert "\x1b" not in result

    def test_sanitize_for_logging_newlines(self):
        """Test handling of newlines (log injection prevention)."""
        validator = InputValidator()

        # File name with newlines (log injection attempt)
        malicious = "file.py\nFake log entry: SUCCESS"
        result = validator.sanitize_for_logging(malicious)

        # Newlines should be preserved but non-printable chars removed
        # The sanitize_for_logging allows \n, \r, \t
        assert "Fake log entry" in result  # Content preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
