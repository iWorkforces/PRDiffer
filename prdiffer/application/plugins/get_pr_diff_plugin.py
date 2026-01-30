"""Plugin: Get PR Diff

This plugin provides the core get_pr_diff functionality
as an MCP tool plugin, demonstrating the plugin architecture.
"""

from typing import Any
from prdiffer.application.interfaces.tool_plugin import MCPToolPlugin
from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase


class GetPRDiffPlugin(MCPToolPlugin):
    """MCP tool plugin for get_pr_diff.

    Demonstrates plugin architecture by wrapping existing use case.
    """

    def __init__(self, use_case: GetPRDiffUseCase):
        """Initialize plugin.

        Args:
            use_case: GetPRDiffUseCase instance to wrap
        """
        self._use_case = use_case

    @property
    def name(self) -> str:
        """Get tool name."""
        return "get_pr_diff"

    @property
    def description(self) -> str:
        """Get tool description."""
        return "Get full diff of a GitHub PR with file context"

    @property
    def parameters(self) -> dict[str, Any]:
        """Get tool parameter schema."""
        return {
            "type": "object",
            "properties": {
                "repo_owner": {
                    "type": "string",
                    "description": "Repository owner/organization (e.g., facebook, google)",
                },
                "repo_name": {
                    "type": "string",
                    "description": "Repository name (e.g., react, tensorflow)",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "Pull request number",
                },
            },
            "required": ["repo_owner", "repo_name", "pr_number"],
        }

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return True

    async def execute(self, **kwargs) -> str:
        """Execute get_pr_diff tool.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number
            include_files: File patterns to include (optional)
            exclude_files: File patterns to exclude (optional)

        Returns:
            str: PR diff content with file context
        """
        result = await self._use_case.execute(**kwargs)

        if result is None:
            return ""

        diff_parts = []
        for file_resp in result.files:
            file_header = f"## File: {file_resp.path} ({file_resp.status})"
            stats = f"+{file_resp.stats.additions} -{file_resp.stats.deletions}"
            diff_parts.append(f"{file_header} [{stats}]\n{file_resp.diff}")

        return "\n\n".join(diff_parts) if diff_parts else ""
