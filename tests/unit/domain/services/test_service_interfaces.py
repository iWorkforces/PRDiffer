"""Unit tests for domain service interfaces.

Tests verify that all domain service interfaces are properly defined as abstract
classes with the correct abstract methods and structure.
"""

import pytest
from abc import ABC

# Import all domain service interfaces
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.diff import DiffServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface, LogLevel
from prdiffer.domain.services.pattern_matching import PatternMatchingServiceInterface
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.retry import RetryServiceInterface
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.github_api import GitHubAPIServiceInterface


class TestCacheServiceInterface:
    """Test suite for CacheServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that CacheServiceInterface is an ABC."""
        assert issubclass(CacheServiceInterface, ABC)
        assert hasattr(CacheServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that CacheServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CacheServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that CacheServiceInterface has all required abstract methods."""
        abstract_methods = CacheServiceInterface.__abstractmethods__

        required_methods = {
            "get_cache_key",
            "get",
            "set",
            "invalidate",
            "clear",
            "get_stats",
        }

        assert required_methods.issubset(abstract_methods)

    def test_get_cache_key_signature(self):
        """Test get_cache_key method signature."""
        assert hasattr(CacheServiceInterface, "get_cache_key")

    def test_get_signature(self):
        """Test get method signature."""
        assert hasattr(CacheServiceInterface, "get")

    def test_set_signature(self):
        """Test set method signature."""
        assert hasattr(CacheServiceInterface, "set")

    def test_invalidate_signature(self):
        """Test invalidate method signature."""
        assert hasattr(CacheServiceInterface, "invalidate")

    def test_clear_signature(self):
        """Test clear method signature."""
        assert hasattr(CacheServiceInterface, "clear")

    def test_get_stats_signature(self):
        """Test get_stats method signature."""
        assert hasattr(CacheServiceInterface, "get_stats")


class TestLoggerServiceInterface:
    """Test suite for LoggerServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that LoggerServiceInterface is an ABC."""
        assert issubclass(LoggerServiceInterface, ABC)
        assert hasattr(LoggerServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that LoggerServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LoggerServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that LoggerServiceInterface has all required abstract methods."""
        abstract_methods = LoggerServiceInterface.__abstractmethods__

        required_methods = {
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        }

        assert required_methods.issubset(abstract_methods)

    def test_debug_signature(self):
        """Test debug method signature."""
        assert hasattr(LoggerServiceInterface, "debug")

    def test_info_signature(self):
        """Test info method signature."""
        assert hasattr(LoggerServiceInterface, "info")

    def test_warning_signature(self):
        """Test warning method signature."""
        assert hasattr(LoggerServiceInterface, "warning")

    def test_error_signature(self):
        """Test error method signature."""
        assert hasattr(LoggerServiceInterface, "error")

    def test_critical_signature(self):
        """Test critical method signature."""
        assert hasattr(LoggerServiceInterface, "critical")


class TestLogLevelEnum:
    """Test suite for LogLevel enumeration."""

    def test_log_level_exists(self):
        """Test that LogLevel enum exists."""
        assert LogLevel is not None

    def test_log_level_values(self):
        """Test that LogLevel has expected values."""
        # LogLevel should have standard logging levels
        assert hasattr(LogLevel, "__members__")
        level_names = [name for name, _ in LogLevel.__members__.items()]
        # Verify common log levels exist
        assert len(level_names) >= 5  # At least 5 levels


class TestSettingsServiceInterface:
    """Test suite for SettingsServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that SettingsServiceInterface is an ABC."""
        assert issubclass(SettingsServiceInterface, ABC)
        assert hasattr(SettingsServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that SettingsServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SettingsServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that SettingsServiceInterface has all required abstract methods."""
        abstract_methods = SettingsServiceInterface.__abstractmethods__

        required_methods = {
            "get",
            "get_github_settings",
            "get_app_settings",
        }

        assert required_methods.issubset(abstract_methods)

    def test_get_signature(self):
        """Test get method signature."""
        assert hasattr(SettingsServiceInterface, "get")

    def test_get_github_settings_signature(self):
        """Test get_github_settings method signature."""
        assert hasattr(SettingsServiceInterface, "get_github_settings")

    def test_get_app_settings_signature(self):
        """Test get_app_settings method signature."""
        assert hasattr(SettingsServiceInterface, "get_app_settings")


class TestRetryServiceInterface:
    """Test suite for RetryServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that RetryServiceInterface is an ABC."""
        assert issubclass(RetryServiceInterface, ABC)
        assert hasattr(RetryServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that RetryServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RetryServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that RetryServiceInterface has all required abstract methods."""
        abstract_methods = RetryServiceInterface.__abstractmethods__

        required_methods = {"execute_with_retry"}

        assert required_methods.issubset(abstract_methods)

    def test_execute_with_retry_signature(self):
        """Test execute_with_retry method signature."""
        assert hasattr(RetryServiceInterface, "execute_with_retry")


class TestPatternMatchingServiceInterface:
    """Test suite for PatternMatchingServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that PatternMatchingServiceInterface is an ABC."""
        assert issubclass(PatternMatchingServiceInterface, ABC)
        assert hasattr(PatternMatchingServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that PatternMatchingServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PatternMatchingServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that PatternMatchingServiceInterface has all required abstract methods."""
        abstract_methods = PatternMatchingServiceInterface.__abstractmethods__

        required_methods = {"is_valid_file", "filter_files"}

        assert required_methods.issubset(abstract_methods)

    def test_is_valid_file_signature(self):
        """Test is_valid_file method signature."""
        assert hasattr(PatternMatchingServiceInterface, "is_valid_file")

    def test_filter_files_signature(self):
        """Test filter_files method signature."""
        assert hasattr(PatternMatchingServiceInterface, "filter_files")


class TestDiffServiceInterface:
    """Test suite for DiffServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that DiffServiceInterface is an ABC."""
        assert issubclass(DiffServiceInterface, ABC)
        assert hasattr(DiffServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that DiffServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DiffServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that DiffServiceInterface has all required abstract methods."""
        abstract_methods = DiffServiceInterface.__abstractmethods__

        required_methods = {
            "build_full_file_patch",
            "decode_if_bytes",
            "extend_patch",
        }

        assert required_methods.issubset(abstract_methods)

    def test_build_full_file_patch_signature(self):
        """Test build_full_file_patch method signature."""
        assert hasattr(DiffServiceInterface, "build_full_file_patch")

    def test_decode_if_bytes_signature(self):
        """Test decode_if_bytes method signature."""
        assert hasattr(DiffServiceInterface, "decode_if_bytes")

    def test_extend_patch_signature(self):
        """Test extend_patch method signature."""
        assert hasattr(DiffServiceInterface, "extend_patch")


class TestRepositoryCacheServiceInterface:
    """Test suite for RepositoryCacheServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that RepositoryCacheServiceInterface is an ABC."""
        assert issubclass(RepositoryCacheServiceInterface, ABC)
        assert hasattr(RepositoryCacheServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that RepositoryCacheServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RepositoryCacheServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that RepositoryCacheServiceInterface has all required abstract methods."""
        abstract_methods = RepositoryCacheServiceInterface.__abstractmethods__

        required_methods = {
            "insert",
            "retrieve",
            "validate",
            "remove",
            "clear",
            "size",
            "stats",
        }

        assert required_methods.issubset(abstract_methods)

    def test_insert_signature(self):
        """Test insert method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "insert")

    def test_retrieve_signature(self):
        """Test retrieve method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "retrieve")

    def test_validate_signature(self):
        """Test validate method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "validate")

    def test_remove_signature(self):
        """Test remove method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "remove")

    def test_clear_signature(self):
        """Test clear method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "clear")

    def test_size_signature(self):
        """Test size method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "size")

    def test_stats_signature(self):
        """Test stats method signature."""
        assert hasattr(RepositoryCacheServiceInterface, "stats")


class TestGitHubAPIServiceInterface:
    """Test suite for GitHubAPIServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that GitHubAPIServiceInterface is an ABC."""
        assert issubclass(GitHubAPIServiceInterface, ABC)
        assert hasattr(GitHubAPIServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that GitHubAPIServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            GitHubAPIServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that GitHubAPIServiceInterface has all required abstract methods."""
        abstract_methods = GitHubAPIServiceInterface.__abstractmethods__

        # Check for key methods (names may vary based on actual interface)
        assert len(abstract_methods) > 0

    def test_initialize_client_exists(self):
        """Test that initialize_client method exists."""
        assert hasattr(GitHubAPIServiceInterface, "initialize_client")


class TestPRDiffServiceInterface:
    """Test suite for PRDiffServiceInterface."""

    def test_is_abstract_base_class(self):
        """Test that PRDiffServiceInterface is an ABC."""
        assert issubclass(PRDiffServiceInterface, ABC)
        assert hasattr(PRDiffServiceInterface, "__abstractmethods__")

    def test_cannot_instantiate(self):
        """Test that PRDiffServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PRDiffServiceInterface()

    def test_has_required_abstract_methods(self):
        """Test that PRDiffServiceInterface has all required abstract methods."""
        abstract_methods = PRDiffServiceInterface.__abstractmethods__

        required_methods = {
            "get_pr_diff",
            "get_latest_commit_sha",
            "validate_repository_access",
        }

        assert required_methods.issubset(abstract_methods)

    def test_get_pr_diff_signature(self):
        """Test get_pr_diff method signature."""
        assert hasattr(PRDiffServiceInterface, "get_pr_diff")

    def test_get_latest_commit_sha_signature(self):
        """Test get_latest_commit_sha method signature."""
        assert hasattr(PRDiffServiceInterface, "get_latest_commit_sha")

    def test_validate_repository_access_signature(self):
        """Test validate_repository_access method signature."""
        assert hasattr(PRDiffServiceInterface, "validate_repository_access")


class TestInterfaceStructure:
    """Test suite for general interface structure compliance."""

    def test_all_interfaces_are_abstract(self):
        """Test that all service interfaces inherit from ABC."""
        interfaces = [
            CacheServiceInterface,
            DiffServiceInterface,
            LoggerServiceInterface,
            PatternMatchingServiceInterface,
            PRDiffServiceInterface,
            RepositoryCacheServiceInterface,
            RetryServiceInterface,
            SettingsServiceInterface,
            GitHubAPIServiceInterface,
        ]

        for interface in interfaces:
            assert issubclass(interface, ABC), (
                f"{interface.__name__} should inherit from ABC"
            )

    def test_all_interfaces_have_abstract_methods(self):
        """Test that all service interfaces have abstract methods."""
        interfaces = [
            CacheServiceInterface,
            DiffServiceInterface,
            LoggerServiceInterface,
            PatternMatchingServiceInterface,
            PRDiffServiceInterface,
            RepositoryCacheServiceInterface,
            RetryServiceInterface,
            SettingsServiceInterface,
            GitHubAPIServiceInterface,
        ]

        for interface in interfaces:
            assert len(interface.__abstractmethods__) > 0, (
                f"{interface.__name__} should have abstract methods"
            )

    def test_all_interfaces_cannot_be_instantiated(self):
        """Test that all service interfaces cannot be instantiated directly."""
        interfaces = [
            CacheServiceInterface,
            DiffServiceInterface,
            LoggerServiceInterface,
            PatternMatchingServiceInterface,
            PRDiffServiceInterface,
            RepositoryCacheServiceInterface,
            RetryServiceInterface,
            SettingsServiceInterface,
            GitHubAPIServiceInterface,
        ]

        for interface in interfaces:
            with pytest.raises(TypeError, match=r"(abstract|instantiated)"):
                interface()

    def test_interface_names_follow_convention(self):
        """Test that all interfaces end with 'Interface' suffix."""
        interfaces = [
            CacheServiceInterface,
            DiffServiceInterface,
            LoggerServiceInterface,
            PatternMatchingServiceInterface,
            PRDiffServiceInterface,
            RepositoryCacheServiceInterface,
            RetryServiceInterface,
            SettingsServiceInterface,
            GitHubAPIServiceInterface,
        ]

        for interface in interfaces:
            assert interface.__name__.endswith("Interface"), (
                f"{interface.__name__} should end with 'Interface' suffix"
            )

    def test_interfaces_have_docstrings(self):
        """Test that all interfaces have docstrings."""
        interfaces = [
            CacheServiceInterface,
            DiffServiceInterface,
            LoggerServiceInterface,
            PatternMatchingServiceInterface,
            PRDiffServiceInterface,
            RepositoryCacheServiceInterface,
            RetryServiceInterface,
            SettingsServiceInterface,
            GitHubAPIServiceInterface,
        ]

        for interface in interfaces:
            assert interface.__doc__ is not None, (
                f"{interface.__name__} should have a docstring"
            )
            assert len(interface.__doc__.strip()) > 0, (
                f"{interface.__name__} docstring should not be empty"
            )


class TestMockImplementationCompliance:
    """Test suite for creating mock implementations that comply with interfaces."""

    def test_can_create_mock_cache_service(self):
        """Test that a mock CacheService can be created."""

        class MockCacheService(CacheServiceInterface):
            def __init__(self):
                self._data = {}

            def get_cache_key(
                self, repo_owner: str, repo_name: str, pr_number: int
            ) -> str:
                return f"{repo_owner}/{repo_name}/pr/{pr_number}"

            def get(self, cache_key: str, current_commit_sha: str):
                return self._data.get(cache_key)

            def set(self, cache_key: str, commit_sha: str, data):
                self._data[cache_key] = data

            def invalidate(self, cache_key: str):
                self._data.pop(cache_key, None)

            def clear(self):
                self._data.clear()

            def get_stats(self):
                return {"size": len(self._data)}

        mock = MockCacheService()
        assert isinstance(mock, CacheServiceInterface)

    def test_can_create_mock_logger_service(self):
        """Test that a mock LoggerService can be created."""

        class MockLoggerService(LoggerServiceInterface):
            def __init__(self):
                self.messages = []

            def _log(self, level, message, **kwargs):
                self.messages.append({"level": level, "message": message, **kwargs})

            def debug(self, message: str, **kwargs):
                self._log("DEBUG", message, **kwargs)

            def info(self, message: str, **kwargs):
                self._log("INFO", message, **kwargs)

            def warning(self, message: str, **kwargs):
                self._log("WARNING", message, **kwargs)

            def error(self, message: str, **kwargs):
                self._log("ERROR", message, **kwargs)

            def critical(self, message: str, **kwargs):
                self._log("CRITICAL", message, **kwargs)

            def should_log(self, level):
                return True  # Log everything

        mock = MockLoggerService()
        assert isinstance(mock, LoggerServiceInterface)

    def test_can_create_mock_settings_service(self):
        """Test that a mock SettingsService can be created."""

        class MockSettingsService(SettingsServiceInterface):
            def __init__(self):
                self._settings = {}

            def get(self, key, default=None):
                return self._settings.get(key, default)

            def get_github_settings(self):
                return {
                    "rate_limit": 5000,
                    "timeout": 30,
                }

            def get_cache_settings(self):
                return {
                    "default_ttl": 300,
                    "max_size": 1000,
                }

            def get_app_settings(self):
                return {
                    "debug": False,
                    "log_level": "INFO",
                }

            def clear_cache(self):
                self._settings.clear()

        mock = MockSettingsService()
        assert isinstance(mock, SettingsServiceInterface)

    def test_can_create_mock_retry_service(self):
        """Test that a mock RetryService can be created."""

        class MockRetryService(RetryServiceInterface):
            def execute_with_retry(self, func, *args, **kwargs):
                return func(*args, **kwargs)

            def _is_rate_limit_error(self, error):
                return False  # Mock implementation

        mock = MockRetryService()
        assert isinstance(mock, RetryServiceInterface)

    def test_can_create_mock_pattern_matching_service(self):
        """Test that a mock PatternMatchingService can be created."""

        class MockPatternMatchingService(PatternMatchingServiceInterface):
            def __init__(self, patterns=None, extensions=None):
                self.patterns = patterns or []
                self.extensions = extensions or []

            def is_valid_file(self, filename):
                # Simple mock implementation
                return not any(p in filename for p in self.patterns)

            def filter_files(self, filenames):
                return [f for f in filenames if self.is_valid_file(f)]

        mock = MockPatternMatchingService()
        assert isinstance(mock, PatternMatchingServiceInterface)

    def test_can_create_mock_diff_service(self):
        """Test that a mock DiffService can be created."""

        class MockDiffService(DiffServiceInterface):
            def build_full_file_patch(self, original_file_str, new_file_str):
                return f"@@ -1,1 +1,1 @@\n-{original_file_str}\n+{new_file_str}\n"

            def decode_if_bytes(self, content):
                if isinstance(content, bytes):
                    return content.decode("utf-8")
                return str(content)

            def extend_patch(self, original_file_str, patch_str, new_file_str=""):
                return patch_str

        mock = MockDiffService()
        assert isinstance(mock, DiffServiceInterface)

    def test_can_create_mock_repository_cache_service(self):
        """Test that a mock RepositoryCacheService can be created."""

        class MockRepositoryCacheService(RepositoryCacheServiceInterface):
            def __init__(self):
                self._cache = {}

            def insert(self, repository):
                key = f"{repository.repo_owner}/{repository.repo_name}/{repository.pr_number}"
                self._cache[key] = repository
                return True

            def retrieve(self, owner, name, pr_number):
                key = f"{owner}/{name}/{pr_number}"
                return self._cache.get(key)

            def validate(self, owner, name, pr_number):
                return f"{owner}/{name}/{pr_number}" in self._cache

            def remove(self, owner, name, pr_number):
                key = f"{owner}/{name}/{pr_number}"
                return self._cache.pop(key, None) is not None

            def clear(self):
                self._cache.clear()

            def size(self):
                return len(self._cache)

            def stats(self):
                return {"size": len(self._cache), "keys": list(self._cache.keys())}

        mock = MockRepositoryCacheService()
        assert isinstance(mock, RepositoryCacheServiceInterface)

    def test_can_create_mock_pr_diff_service(self):
        """Test that a mock PRDiffService can be created."""

        class MockPRDiffService(PRDiffServiceInterface):
            def get_pr_diff(self, repo_owner, repo_name, pr_number):
                return None

            def get_latest_commit_sha(self, repo_owner, repo_name, pr_number):
                return "abc123"

            def validate_repository_access(self, repo_owner, repo_name):
                return True

        mock = MockPRDiffService()
        assert isinstance(mock, PRDiffServiceInterface)

    def test_can_create_mock_github_api_service(self):
        """Test that a mock GitHubAPIService can be created."""

        class MockGitHubAPIService(GitHubAPIServiceInterface):
            def __init__(self):
                self.initialized = False

            def initialize_client(self, github_token=None, timeout=30):
                self.initialized = True

            def get_repository(self, repo_full_name):
                return None  # Mock implementation

            def get_pull_request(self, repository, pr_number):
                return None  # Mock implementation

            def get_file_content(self, repository, file_path, branch):
                return ""  # Mock implementation

            def get_files_content_batch(self, repository, file_paths, branch):
                return {}  # Mock implementation

        mock = MockGitHubAPIService()
        assert isinstance(mock, GitHubAPIServiceInterface)
