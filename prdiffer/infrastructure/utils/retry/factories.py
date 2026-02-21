"""Retry handler factory functions."""

from prdiffer.infrastructure.utils.retry.handler import UnifiedRetryHandler


def get_retry_handler(**kwargs) -> UnifiedRetryHandler:
    """Get a configured retry handler instance."""
    kwargs.setdefault('use_advanced_features', False)
    return UnifiedRetryHandler(**kwargs)


def get_advanced_retry_handler(**kwargs) -> UnifiedRetryHandler:
    """Get a retry handler with advanced features enabled."""
    kwargs.setdefault('use_advanced_features', True)
    return UnifiedRetryHandler(**kwargs)
