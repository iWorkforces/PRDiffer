"""Unit tests for InfrastructureFactory layer isolation.

Tests verify:
- No application-layer imports at the top level of infrastructure_factory.py
- All service creation methods return correct interface types
- Deprecated methods emit proper warnings
"""

import ast
import warnings
from unittest.mock import Mock

from prdiffer.infrastructure.factories.infrastructure_factory import (
    InfrastructureFactory,
)
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.diff import DiffServiceInterface
from prdiffer.domain.services.pattern_matching import (
    PatternMatchingServiceInterface,
)
from prdiffer.domain.services.retry import RetryServiceInterface


class TestInfrastructureFactoryLayerIsolation:
    """Test suite for infrastructure factory layer isolation."""

    def test_no_application_imports_at_top_level(self):
        """Test that infrastructure_factory.py has NO top-level imports from prdiffer.application."""
        # Parse the infrastructure_factory.py file
        with open(
            "prdiffer/infrastructure/factories/infrastructure_factory.py", "r"
        ) as f:
            tree = ast.parse(f.read())

        # Collect all top-level imports
        application_imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Check if it's an import from prdiffer.application
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("prdiffer.application"):
                        application_imports.append(
                            f"from {node.module} import {[alias.name for alias in node.names]}"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("prdiffer.application"):
                            application_imports.append(f"import {alias.name}")

        # Assert that NO application-layer imports exist at top level
        assert len(application_imports) == 0, (
            f"Found top-level application-layer imports: {application_imports}"
        )

    def test_creates_settings_service(self):
        """Test that create_settings_service returns SettingsServiceInterface."""
        factory = InfrastructureFactory()
        settings_service = factory.create_settings_service()

        assert isinstance(settings_service, SettingsServiceInterface)
        assert settings_service is not None

    def test_creates_logger_service(self):
        """Test that create_logger_service returns LoggerServiceInterface."""
        factory = InfrastructureFactory()
        logger_service = factory.create_logger_service()

        assert isinstance(logger_service, LoggerServiceInterface)
        assert logger_service is not None

    def test_creates_cache_service(self):
        """Test that create_cache_service returns CacheServiceInterface."""
        factory = InfrastructureFactory()
        cache_service = factory.create_cache_service()

        assert isinstance(cache_service, CacheServiceInterface)
        assert cache_service is not None

    def test_creates_diff_service(self):
        """Test that create_diff_service returns DiffServiceInterface."""
        factory = InfrastructureFactory()
        diff_service = factory.create_diff_service()

        assert isinstance(diff_service, DiffServiceInterface)
        assert diff_service is not None

    def test_creates_pattern_matching_service(self):
        """Test that create_pattern_matching_service returns PatternMatchingServiceInterface."""
        factory = InfrastructureFactory()
        pattern_matching_service = factory.create_pattern_matching_service()

        assert isinstance(pattern_matching_service, PatternMatchingServiceInterface)
        assert pattern_matching_service is not None

    def test_creates_retry_service(self):
        """Test that create_retry_service returns RetryServiceInterface."""
        factory = InfrastructureFactory()
        retry_service = factory.create_retry_service()

        assert isinstance(retry_service, RetryServiceInterface)
        assert retry_service is not None


class TestInfrastructureFactoryDeprecatedMethods:
    """Test suite for deprecated methods in InfrastructureFactory."""

    def test_create_rate_limiter_emits_deprecation_warning(self):
        """Test that create_rate_limiter emits DeprecationWarning."""
        factory = InfrastructureFactory()
        mock_logger = Mock(spec=LoggerServiceInterface)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _result = factory.create_rate_limiter(mock_logger)  # noqa: F841

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ApplicationFactory" in str(w[0].message)

    def test_create_metrics_tracker_emits_deprecation_warning(self):
        """Test that create_metrics_tracker emits DeprecationWarning."""
        factory = InfrastructureFactory()
        mock_logger = Mock(spec=LoggerServiceInterface)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _result = factory.create_metrics_tracker(mock_logger)  # noqa: F841

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ApplicationFactory" in str(w[0].message)

    def test_create_pr_operation_handler_emits_deprecation_warning(self):
        """Test that create_pr_operation_handler emits DeprecationWarning."""
        factory = InfrastructureFactory()
        mock_logger = Mock(spec=LoggerServiceInterface)
        mock_cache = Mock(spec=CacheServiceInterface)
        mock_repo_cache = Mock()
        mock_diff = Mock(spec=DiffServiceInterface)
        mock_pattern = Mock(spec=PatternMatchingServiceInterface)
        mock_retry = Mock(spec=RetryServiceInterface)
        mock_github_class = Mock()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _result = factory.create_pr_operation_handler(  # noqa: F841
                github_repository_class=mock_github_class,
                cache_service=mock_cache,
                repository_cache_service=mock_repo_cache,
                diff_service=mock_diff,
                pattern_matching_service=mock_pattern,
                retry_service=mock_retry,
                logger=mock_logger,
            )

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ApplicationFactory" in str(w[0].message)

    def test_create_health_monitor_emits_deprecation_warning(self):
        """Test that create_health_monitor emits DeprecationWarning."""
        factory = InfrastructureFactory()
        mock_logger = Mock(spec=LoggerServiceInterface)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _result = factory.create_health_monitor(  # noqa: F841
                metrics_tracker=Mock(),
                rate_limiter=Mock(),
                logger=mock_logger,
            )

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ApplicationFactory" in str(w[0].message)

    def test_create_server_configuration_emits_deprecation_warning(self):
        """Test that create_server_configuration emits DeprecationWarning."""
        factory = InfrastructureFactory()
        mock_logger = Mock(spec=LoggerServiceInterface)
        mock_settings = Mock(spec=SettingsServiceInterface)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _result = factory.create_server_configuration(  # noqa: F841
                settings_service=mock_settings,
                logger=mock_logger,
            )

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ApplicationFactory" in str(w[0].message)

    def test_create_authentication_emits_deprecation_warning(self):
        """Test that create_authentication emits DeprecationWarning."""
        factory = InfrastructureFactory()
        mock_logger = Mock(spec=LoggerServiceInterface)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _result = factory.create_authentication(mock_logger)  # noqa: F841

            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "ApplicationFactory" in str(w[0].message)
