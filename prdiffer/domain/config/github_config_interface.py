"""Interface for GitHub configuration.

This module defines the abstract interface for GitHub configuration,
enabling dependency inversion and testability.

Note: This interface uses Protocol-like typing rather than ABC to work
better with dataclasses. Type checkers will verify compatibility.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class GitHubConfigInterface(Protocol):
    """Interface for GitHub configuration.

    This protocol defines the contract for GitHub configuration objects,
    allowing different implementations while maintaining type safety
    and enabling dependency injection for testing.

    Protocol is used instead of ABC to work better with dataclasses,
    as dataclass fields automatically provide the required attributes.
    """

    # Core configuration attributes (dataclass fields)

    rate_limit: int
    timeout: int
    max_retries: int
    retry_delay: float
    retry_on_404: bool
    retry_on_403: bool
    retry_on_500: bool
    circuit_breaker_enabled: bool
    diff_parallel_enabled: bool
    diff_parallel_threshold: int
    diff_max_workers: int
    ignore_patterns: tuple[str, ...]
    valid_extensions: tuple[str, ...]
    max_files_allowed: int

    # Methods for configuration operations

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns:
            dict: Dictionary representation of configuration
        """

    def with_overrides(self, **kwargs) -> "GitHubConfigInterface":
        """Create new config with overridden values.

        Args:
            **kwargs: Values to override

        Returns:
            GitHubConfigInterface: New configuration with overrides applied
        """

    # Properties for derived values

    @property
    def should_use_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be used."""

    @property
    def should_use_parallel_diff(self) -> bool:
        """Check if parallel diff processing should be used."""

    # Methods for file validation

    def should_ignore_file(self, filename: str) -> bool:
        """Check if a file should be ignored based on patterns.

        Args:
            filename: File path to check

        Returns:
            bool: True if file should be ignored
        """

    def has_valid_extension(self, filename: str) -> bool:
        """Check if a file has a valid extension.

        Args:
            filename: File path to check

        Returns:
            bool: True if file has valid extension
        """

    def should_process_file(self, filename: str) -> bool:
        """Check if a file should be processed.

        Args:
            filename: File path to check

        Returns:
            bool: True if file should be processed
        """
