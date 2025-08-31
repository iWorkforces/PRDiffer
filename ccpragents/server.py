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
from infrastructure.prompt_repository import get_prompt_repository
from infrastructure.github_repository import GitHubPRDiffRepository
from domain.usecases.prompt_usecases import DescribePRUseCase, ReviewPRUseCase, UpdateChangelogUseCase

def main():
    print("🚀 Starting MCP Server For Fetching GitHub PR's Diff...")
    load_dotenv()

    # Initialize dependencies following clean architecture principles
    settings_service = get_settings_service()
    cache_service = get_cache_service()
    repository_cache_service = get_repository_cache_service()
    logger = get_logger()

    # Initialize prompt repository and use cases
    prompt_repository = get_prompt_repository()
    describe_use_case = DescribePRUseCase(prompt_repository)
    review_use_case = ReviewPRUseCase(prompt_repository)
    update_changelog_use_case = UpdateChangelogUseCase(prompt_repository)

    # Create server with dependency injection
    server: FastMCPServer = FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        logger=logger,
        github_repository_class=GitHubPRDiffRepository,
        describe_use_case=describe_use_case,
        review_use_case=review_use_case,
        update_changelog_use_case=update_changelog_use_case
    )
    server.run()

if __name__ == "__main__":
    main()
