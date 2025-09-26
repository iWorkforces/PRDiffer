"""Server configuration component for setup and configuration management."""

import logging
from typing import Dict, Any, Optional
from ..interfaces.protocols import ServerConfigurationProtocol


class ServerConfiguration(ServerConfigurationProtocol):
    """Component responsible for server configuration and setup."""

    def __init__(
        self,
        settings_service,  # SettingsServiceInterface
        logger: Optional[Any] = None,
    ):
        """Initialize server configuration.

        Args:
            settings_service: Settings service for configuration management
            logger: Optional logger instance
        """
        self._settings_service = settings_service
        self._logger = logger or logging.getLogger(__name__)

    def setup_logging(self) -> None:
        """Set up logging configuration.

        This method can be extended to configure logging based on settings
        like log level, format, handlers, etc.
        """
        try:
            # Log level configuration
            log_level = self._settings_service.get("logging.level", "INFO").upper()

            # Configure root logger if needed
            root_logger = logging.getLogger()
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                root_logger.setLevel(getattr(logging, log_level))

            self._logger.info(
                f"Logging configuration completed with level: {log_level}"
            )

        except Exception as e:
            self._logger.error(f"Failed to setup logging: {str(e)}")
            # Don't raise exception as logging issues shouldn't prevent server startup

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and configuration.

        Returns:
            Dictionary containing server information
        """
        try:
            return {
                "name": "ccpragents",
                "version": "0.1.3",
                "description": "GitHub PR Diff Fetcher MCP Server",
                "transport": self._settings_service.get("mcp.transport", "stdio"),
                "port": self._settings_service.get("mcp.port", 9101),
                "host": self._settings_service.get("mcp.host", "127.0.0.1"),
                "path": self._settings_service.get("mcp.path", "/mcp"),
                "environment": self._settings_service.get("env", "development"),
                "debug_mode": self._settings_service.get("debug", False),
                "features": {
                    "caching": True,
                    "rate_limiting": True,
                    "metrics_tracking": True,
                    "health_monitoring": True,
                },
            }
        except Exception as e:
            self._logger.error(f"Failed to get server info: {str(e)}")
            return {
                "name": "ccpragents",
                "version": "unknown",
                "description": "GitHub PR Diff Fetcher MCP Server",
                "error": str(e),
            }

    def get_mcp_instructions(self) -> str:
        """Get MCP server instructions for clients.

        Returns:
            String containing MCP server instructions
        """
        return """
CCPRAgents MCP - GitHub Pull Request Analysis Tools

Available Tools:
• get_pr_diff(pr_url, use_cache=True) - Fetch complete PR diff data
• describe_pr(pr_url, commit_messages, diff_content) - Generate PR descriptions
• approve_pr(pr_url, commit_messages, diff_content) - Generate PR approvals
• review_pr(pr_url, commit_messages, diff_content) - Review PRs for quality
• update_pr_changelog(pr_url, commit_messages, diff_content) - Generate changelog entries
• health() - Get server health and metrics

Usage: Call tools with GitHub PR URLs (e.g., "https://github.com/owner/repo/pull/123")
"""

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate server configuration.

        Returns:
            Dictionary with validation results
        """
        validation_results = {"valid": True, "warnings": [], "errors": []}

        try:
            # Check required settings
            transport = self._settings_service.get("mcp.transport", "stdio")
            if transport not in ["stdio", "sse", "http"]:
                validation_results["warnings"].append(
                    f"Unknown transport '{transport}', defaulting to stdio"
                )

            # Check port configuration for non-stdio transports
            if transport != "stdio":
                port = self._settings_service.get("mcp.port", 9101)
                if not isinstance(port, int) or port < 1 or port > 65535:
                    validation_results["errors"].append(
                        f"Invalid port '{port}', must be between 1-65535"
                    )
                    validation_results["valid"] = False

            # Check GitHub configuration if available
            github_token = self._settings_service.get("github.token", None)
            if not github_token:
                validation_results["warnings"].append(
                    "No GitHub token configured, API rate limits may apply"
                )

            self._logger.info(
                f"Configuration validation completed: {validation_results}"
            )

        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(
                f"Configuration validation failed: {str(e)}"
            )
            self._logger.error(f"Configuration validation failed: {str(e)}")

        return validation_results
