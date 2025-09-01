"""URL validation component for GitHub PR URLs."""

import re
from typing import Tuple
from ..interfaces.protocols import URLValidatorProtocol


class URLValidator(URLValidatorProtocol):
    """Component responsible for validating and parsing GitHub PR URLs."""

    def parse_github_url(self, pr_url: str) -> Tuple[str, str, int]:
        """Parse GitHub PR URL to extract repository owner, name, and PR number.

        Args:
            pr_url: The GitHub pull request URL to parse

        Returns:
            Tuple of (repo_owner, repo_name, pr_number)

        Raises:
            ValueError: If the URL format is invalid or contains invalid characters
        """
        if not pr_url:
            raise ValueError("PR URL cannot be empty")

        # Trim whitespace and validate basic URL structure
        pr_url = pr_url.strip()
        if not pr_url.startswith('https://github.com/'):
            raise ValueError("PR URL must be a GitHub URL starting with https://github.com/")

        # Pattern to match GitHub PR URLs with validation
        pattern = r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/pull/(\d+)/?$"
        match = re.match(pattern, pr_url)

        if not match:
            # Provide more helpful error message
            raise ValueError(
                f"Invalid GitHub PR URL format: {pr_url}. "
                "Expected format: https://github.com/owner/repo/pull/123"
            )

        repo_owner = match.group(1)
        repo_name = match.group(2)
        pr_number = int(match.group(3))

        # Additional validation
        if not repo_owner:
            raise ValueError("Repository owner cannot be empty")
        if not repo_name:
            raise ValueError("Repository name cannot be empty")
        if pr_number <= 0:
            raise ValueError(f"PR number must be positive, got {pr_number}")

        return repo_owner, repo_name, pr_number