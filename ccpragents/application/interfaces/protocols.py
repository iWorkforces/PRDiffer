"""Protocol definitions for MCP server components.

This module defines the interfaces that each component must implement,
ensuring loose coupling and enabling easy testing with mocks.
"""

from typing import Dict, Any, Tuple, Protocol, Optional


class URLValidatorProtocol(Protocol):
    """Protocol for URL validation and parsing."""

    def parse_github_url(self, pr_url: str) -> Tuple[str, str, int]:
        """Parse GitHub PR URL and extract owner, repo, and PR number.

        Args:
            pr_url: GitHub PR URL to parse

        Returns:
            Tuple of (owner, repo, pr_number)

        Raises:
            ValueError: If URL format is invalid
        """
        ...


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting functionality."""

    def check_rate_limit(self, identifier: str) -> bool:
        """Check if the request is within rate limits.

        Args:
            identifier: Unique identifier for rate limiting (e.g., IP, user ID)

        Returns:
            True if request is allowed, False if rate limited
        """
        ...

    def increment_rate_limit(self, identifier: str) -> None:
        """Increment the rate limit counter for the identifier.

        Args:
            identifier: Unique identifier for rate limiting
        """
        ...

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit configuration and current status.

        Returns:
            Dictionary with rate limit information
        """
        ...


class MetricsTrackerProtocol(Protocol):
    """Protocol for tracking metrics and request statistics."""

    def track_request(
        self, operation: str, success: bool, execution_time: float
    ) -> None:
        """Track a request for metrics collection.

        Args:
            operation: Name of the operation being tracked
            success: Whether the operation was successful
            execution_time: Time taken to execute the operation in seconds
        """
        ...

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics.

        Returns:
            Dictionary containing metrics data
        """
        ...

    def generate_request_id(self) -> str:
        """Generate a unique request ID for tracking purposes.

        Returns:
            Unique request ID
        """
        ...


class PROperationHandlerProtocol(Protocol):
    """Protocol for handling PR-related operations."""

    async def get_pr_diff(
        self,
        pr_url: str,
        use_cache: bool = True,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        pr_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get PR diff information.

        Args:
            pr_url: GitHub PR URL
            use_cache: Whether to use caching (currently ignored - caching is automatic)
            repo_owner: Repository owner (extracted from URL if not provided)
            repo_name: Repository name (extracted from URL if not provided)
            pr_number: PR number (extracted from URL if not provided)

        Returns:
            Dictionary containing PR diff data
        """
        ...

    async def describe_pr(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Generate PR description based on commit messages and diff.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR
            diff_content: Diff content of the PR

        Returns:
            Generated PR description
        """
        ...

    async def approve_pr(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Generate PR approval message.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR
            diff_content: Diff content of the PR

        Returns:
            Generated approval message
        """
        ...

    async def review_pr(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Generate PR review.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR
            diff_content: Diff content of the PR

        Returns:
            Generated PR review
        """
        ...

    async def update_pr_changelog(
        self, pr_url: str, commit_messages: str, diff_content: str
    ) -> str:
        """Update PR changelog.

        Args:
            pr_url: GitHub PR URL
            commit_messages: Commit messages from the PR
            diff_content: Diff content of the PR

        Returns:
            Updated changelog content
        """
        ...


class HealthMonitorProtocol(Protocol):
    """Protocol for health monitoring and status checks."""

    def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status.

        Returns:
            Dictionary containing health status information
        """
        ...


class ServerConfigurationProtocol(Protocol):
    """Protocol for server configuration and setup."""

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        ...

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and configuration.

        Returns:
            Dictionary containing server information
        """
        ...

    def get_mcp_instructions(self) -> str:
        """Get MCP server instructions for clients.

        Returns:
            String containing MCP server instructions
        """
        ...
