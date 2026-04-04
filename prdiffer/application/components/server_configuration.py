"""Server configuration component."""

import logging

from typing import Any, TypedDict
from prdiffer.domain.interfaces.protocols import ServerConfigurationProtocol
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.version import __version__
from prdiffer.domain.services.logger import LoggerServiceInterface


class ValidationResult(TypedDict):
    valid: bool
    warnings: list[str]
    errors: list[str]


class ServerConfiguration(ServerConfigurationProtocol):
    """Component responsible for server configuration and setup."""

    def __init__(
        self,
        settings_service: SettingsServiceInterface,
        logger: logging.Logger | LoggerServiceInterface | None = None,
    ):
        self._settings_service = settings_service
        self._logger = logger or logging.getLogger(__name__)

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        try:
            log_level = self._settings_service.get("app.log_level", "INFO").upper()

            root_logger = logging.getLogger()
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                root_logger.setLevel(getattr(logging, log_level))

            self._logger.info(f"Logging configuration completed with level: {log_level}")

        except Exception as e:
            self._logger.error(f"Failed to setup logging: {str(e)}")

    def get_server_info(self) -> dict[str, Any]:
        """Get server information and configuration."""
        try:
            return {
                "name": "prdiffer",
                "version": __version__,
                "description": "GitHub PR Diff Fetcher MCP Server",
                "transport": self._settings_service.get("mcp.transport", "http"),
                "port": self._settings_service.get("mcp.port", 9102),
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
                "name": "prdiffer",
                "version": "unknown",
                "description": "GitHub PR Diff Fetcher MCP Server",
                "error": str(e),
            }

    def get_mcp_instructions(self) -> str:
        """Get MCP server instructions for clients."""
        return """
        prdiffer MCP server - GitHub Pull Request Analysis Tools

        Available Tools:
            • get_pr_diff(pr_url) - Fetch complete GitHub PR code diff
            • health() - Get server health and metrics

        Usage: Call tools with GitHub PR URLs (e.g., "https://github.com/owner/repo/pull/123")
        """

    def validate_configuration(self) -> ValidationResult:
        """Validate server configuration."""
        validation_results: ValidationResult = {
            "valid": True,
            "warnings": [],
            "errors": [],
        }

        try:
            transport = self._settings_service.get("mcp.transport", "http")
            if transport not in ["stdio", "sse", "http"]:
                validation_results["warnings"].append(f"Unknown transport '{transport}', defaulting to stdio")

            if transport != "stdio":
                port = self._settings_service.get("mcp.port", 9102)
                if not isinstance(port, int) or port < 1 or port > 65535:
                    validation_results["errors"].append(f"Invalid port '{port}', must be between 1-65535")
                    validation_results["valid"] = False

            import os

            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                validation_results["warnings"].append(
                    "No GITHUB_TOKEN environment variable set, API rate limits may apply. Set GITHUB_TOKEN=your_token or add to .env file"
                )

            self._logger.info(f"Configuration validation completed: {validation_results}")

        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Configuration validation failed: {str(e)}")
            self._logger.error(f"Configuration validation failed: {str(e)}")

        return validation_results
