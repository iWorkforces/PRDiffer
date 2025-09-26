import sys
import os
from dotenv import load_dotenv

# Add the current directory to Python path for direct execution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.mcp_server import FastMCPServer
from infrastructure.settings import get_settings_service
from infrastructure.cache_service import get_cache_service
from infrastructure.repository_cache_service import get_repository_cache_service
from infrastructure.logging.console_logger import get_logger
from infrastructure import GitHubPRDiffRepository


def main():
    print("🚀 Starting MCP Server For Fetching GitHub PR's Diff...")
    load_dotenv()

    # Initialize dependencies following clean architecture principles
    settings_service = get_settings_service()
    cache_service = get_cache_service()
    repository_cache_service = get_repository_cache_service()
    logger = get_logger()

    # Create server with dependency injection
    server: FastMCPServer = FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        logger=logger,
        github_repository_class=GitHubPRDiffRepository,
    )
    server.run()


if __name__ == "__main__":
    main()
