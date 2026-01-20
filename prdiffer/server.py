import sys
import os
import argparse
from dotenv import load_dotenv

# Add the current directory to Python path for direct execution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prdiffer.version import __version__
from prdiffer.application.factory import create_mcp_server
from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.infrastructure.cache_service import get_cache_service
from prdiffer.infrastructure.repository_cache_service import (
    get_repository_cache_service,
)
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure import GitHubPRDiffRepository


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        prog="prdiffer",
        description="MCP Server for GitHub PR Review Process with Full Contexts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default http transport
  prdiffer

  # Run as HTTP server
  prdiffer --transport http --port 9102

  # Run with SSE transport
  prdiffer --transport sse --port 9102 --host 0.0.0.0

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token for API authentication
  MCP_TRANSPORT   Override transport mode (http, stdio, sse, streamable-http)
  MCP_PORT        Override server port
  MCP_HOST        Override server host
  MCP_PATH        Override server path
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )

    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http", "sse", "streamable-http"],
        help="Transport protocol (default: http, or from settings.toml)",
    )

    parser.add_argument(
        "--port",
        type=int,
        help="Server port for non-stdio transports (default: 9102)",
    )

    parser.add_argument(
        "--host",
        type=str,
        help="Server host for non-stdio transports (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--path",
        type=str,
        help="Server path for non-stdio transports (default: /mcp)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for the MCP server.

    Supports both CLI argument parsing and environment variable configuration.
    When run as a tool (via `prdiffer` command), defaults to stdio transport.
    """
    # Parse command-line arguments
    args = parse_args()

    # Set environment variables based on CLI args or defaults
    # Priority: CLI args > existing env vars > default (http)
    if args.transport:
        os.environ["MCP_TRANSPORT"] = args.transport
    elif "MCP_TRANSPORT" not in os.environ:
        os.environ["MCP_TRANSPORT"] = "http"

    if args.port:
        os.environ["MCP_PORT"] = str(args.port)

    if args.host:
        os.environ["MCP_HOST"] = args.host

    if args.path:
        os.environ["MCP_PATH"] = args.path

    # Get the transport mode to determine where to print messages
    transport_mode = os.environ.get("MCP_TRANSPORT", "stdio")

    # In stdio mode, ALL output must go to stderr to avoid corrupting JSON-RPC protocol
    # Only JSON-RPC messages should go to stdout in stdio mode
    output_stream = sys.stderr if transport_mode == "stdio" else sys.stdout

    print("🚀 Starting MCP Server For Fetching GitHub PR's Diff...", file=output_stream)
    print(f"📦 Version: {__version__}", file=output_stream)
    print(f"🔧 Transport: {transport_mode}", file=output_stream)

    # Load environment variables from .env file (if present)
    load_dotenv()

    # Initialize dependencies following clean architecture principles
    settings_service = get_settings_service()
    cache_service = get_cache_service()
    repository_cache_service = get_repository_cache_service()
    logger = get_logger()

    # Create server using factory pattern for proper dependency injection
    server = create_mcp_server(
        github_repository_class=GitHubPRDiffRepository,
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        logger=logger,
    )
    server.run()


if __name__ == "__main__":
    main()
