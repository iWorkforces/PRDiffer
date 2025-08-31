'''GitHub infrastructure components for CCPRAgents.

This module contains all GitHub-related infrastructure components including
API client, file processing, diff generation, and parallel execution utilities.
'''

from .api_client import GitHubAPIService, get_github_api_client
from .file_processor import FileProcessor, get_file_processor
from .diff_generator import DiffGenerator, get_diff_generator
from .parallel_executor import ParallelExecutor, get_parallel_executor

__all__ = [
    'GitHubAPIService',
    'get_github_api_client',
    'FileProcessor',
    'get_file_processor',
    'DiffGenerator',
    'get_diff_generator',
    'ParallelExecutor',
    'get_parallel_executor',
]