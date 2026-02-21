"""Tests for concurrency settings in infrastructure layer.

These tests verify that concurrency settings are properly read
from settings.toml and applied to GitHubAPIClient and FileProcessor.
"""

from prdiffer.infrastructure.github.client import GitHubAPIClient
from prdiffer.infrastructure.github.file_processor import FileProcessor
from prdiffer.infrastructure.settings import SettingsService


class TestConcurrencySettings:
    """Test concurrency configuration settings."""

    def test_github_api_client_respects_max_concurrent_setting(self):
        """Verify that GitHubAPIClient uses max_concurrent from settings."""
        settings_service = SettingsService()

        # Default value from settings.toml
        default_max_concurrent = settings_service.get('github.max_concurrent', 4)

        # Create client with default settings
        client = GitHubAPIClient(
            max_concurrent=default_max_concurrent,
            use_advanced_retry=False,
        )

        # Verify executor uses the configured max_concurrent value
        assert client._async_executor.max_concurrent == default_max_concurrent

    def test_github_api_client_can_override_max_concurrent(self):
        """Verify that GitHubAPIClient max_concurrent can be overridden."""
        custom_max_concurrent = 8

        # Create client with custom concurrency
        client = GitHubAPIClient(
            max_concurrent=custom_max_concurrent,
            use_advanced_retry=False,
        )

        # Verify executor uses the custom max_concurrent value
        assert client._async_executor.max_concurrent == custom_max_concurrent

    def test_file_processor_respects_max_workers_setting(self):
        """Verify that FileProcessor uses max_parallel_workers from settings."""
        settings_service = SettingsService()

        # Get default value from settings
        default_max_workers = settings_service.get('file_processing.concurrent_downloads', 3)

        # Create minimal dependencies for testing
        class MockGithubAPIService:
            pass

        class MockPatternMatcher:
            pass

        class MockDiffUtils:
            pass

        # Create file processor with default settings
        processor = FileProcessor(
            github_api_service=MockGithubAPIService(),
            pattern_matcher=MockPatternMatcher(),
            diff_utils=MockDiffUtils(),
            max_parallel_workers=default_max_workers,
        )

        # Verify executor uses the configured max_parallel_workers value
        assert processor._async_executor.max_concurrent == default_max_workers

    def test_file_processor_can_override_max_workers(self):
        """Verify that FileProcessor max_parallel_workers can be overridden."""
        custom_max_workers = 10

        # Create minimal dependencies for testing
        class MockGithubAPIService:
            pass

        class MockPatternMatcher:
            pass

        class MockDiffUtils:
            pass

        # Create file processor with custom workers
        processor = FileProcessor(
            github_api_service=MockGithubAPIService(),
            pattern_matcher=MockPatternMatcher(),
            diff_utils=MockDiffUtils(),
            max_parallel_workers=custom_max_workers,
        )

        # Verify executor uses the custom max_parallel_workers value
        assert processor._async_executor.max_concurrent == custom_max_workers

    def test_concurrency_settings_have_reasonable_defaults(self):
        """Verify that default concurrency settings are reasonable values."""
        settings_service = SettingsService()

        # Check GitHub API client default
        github_max_concurrent = settings_service.get('github.max_concurrent', 4)
        assert 1 <= github_max_concurrent <= 20, 'GitHub max_concurrent should be between 1 and 20'

        # Check FileProcessor default
        file_max_workers = settings_service.get('file_processing.concurrent_downloads', 3)
        assert 1 <= file_max_workers <= 20, 'File max_workers should be between 1 and 20'

    def test_async_parallel_executor_configurable(self):
        """Verify that AsyncParallelExecutor can be configured with different concurrency values."""
        from prdiffer.infrastructure.utils.parallel import (
            AsyncParallelExecutor,
            ErrorStrategy,
        )

        # Test with different concurrency values
        for max_concurrent in [1, 4, 8, 16]:
            executor = AsyncParallelExecutor(
                max_concurrent=max_concurrent,
                error_strategy=ErrorStrategy.IGNORE,
            )
            assert executor.max_concurrent == max_concurrent
