"""CCPRAgents - MCP Server for GitHub PR Review Process with Full Contexts.

This package provides a Model Context Protocol (MCP) server that enables
AI assistants to analyze GitHub pull requests with comprehensive diff context.
"""

__version__ = "0.3.1"

# Export main components for programmatic access
from ccpragents.server import main

__all__ = ["main", "__version__"]
