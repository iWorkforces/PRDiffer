"""GitHub infrastructure components for PRDiffer.

This module contains all GitHub-related infrastructure components including
API client, file processing, diff generation, and parallel execution utilities.
"""

from .client import GitHubAPIClient, get_github_api_client
from .file_processor import FileProcessor, get_file_processor
from .diff_generator import DiffGenerator, get_diff_generator

__all__ = [
    "GitHubAPIClient",
    "get_github_api_client",
    "FileProcessor",
    "get_file_processor",
    "DiffGenerator",
    "get_diff_generator",
]
