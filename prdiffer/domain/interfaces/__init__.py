"""Domain interfaces module.

This module re-exports all protocol definitions from the domain layer,
following Clean Architecture principles where domain interfaces should
not depend on application or infrastructure layers.
"""

from prdiffer.domain.interfaces.protocols import (
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
    AuthenticationProtocol,
)
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface

__all__ = [
    'RateLimiterProtocol',
    'MetricsTrackerProtocol',
    'PROperationHandlerProtocol',
    'HealthMonitorProtocol',
    'ServerConfigurationProtocol',
    'AuthenticationProtocol',
    'VCSDiffRepositoryInterface',
]
