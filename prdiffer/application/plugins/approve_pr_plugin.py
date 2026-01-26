"""Plugin: Approve PR

This plugin provides approve_pr functionality as an MCP tool plugin,
allowing PR approval with compliment comments.
"""

from typing import Dict, Any
from prdiffer.application.interfaces.tool_plugin import MCPToolPlugin
from prdiffer.domain.usecases.pr_approval_usecases import ApprovePRUseCase


class ApprovePRPlugin(MCPToolPlugin):
    """MCP tool plugin for approve_pr.

    This plugin enables approving GitHub pull requests with compliment comments
    through the MCP protocol, following the plugin architecture.
    """

    def __init__(self, use_case: ApprovePRUseCase):
        """Initialize plugin.

        Args:
            use_case: ApprovePRUseCase instance to wrap
        """
        self._use_case = use_case

    @property
    def name(self) -> str:
        """Get tool name."""
        return "approve_pr"

    @property
    def description(self) -> str:
        """Get tool description."""
        return "Approve a GitHub PR with a compliment comment"

    @property
    def parameters(self) -> Dict[str, Any]:
        """Get tool parameter schema."""
        return {
            "type": "object",
            "properties": {
                "compliment": {
                    "type": "string",
                    "description": "The compliment text to include in the approval review",
                },
                "pr_url": {
                    "type": "string",
                    "description": "The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)",
                },
            },
            "required": ["compliment", "pr_url"],
        }

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return True

    @property
    def category(self) -> str:
        """Get tool category for organization."""
        return "pr-operations"

    async def execute(self, **kwargs) -> str:
        """Execute approve_pr tool.

        Args:
            compliment: The compliment text to include in the approval review
            pr_url: The full GitHub PR URL

        Returns:
            str: Result message from approval operation

        Raises:
            ValueError: If required parameters missing
            RuntimeError: If execution fails
        """
        # Extract parameters from kwargs
        compliment = kwargs.get("compliment")
        pr_url = kwargs.get("pr_url")

        # Validate required parameters
        if not compliment:
            raise ValueError("compliment is required")

        if not pr_url:
            raise ValueError("pr_url is required")

        if not isinstance(compliment, str):
            raise ValueError(
                f"compliment must be a string, got {type(compliment).__name__}"
            )

        if not isinstance(pr_url, str):
            raise ValueError(f"pr_url must be a string, got {type(pr_url).__name__}")

        # Execute use case
        result = await self._use_case.execute(
            pr_url=pr_url,
            compliment=compliment,
        )

        return result
