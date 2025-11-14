#!/usr/bin/env python3
"""Simple test script to verify GitHub client initialization and functionality."""

import asyncio
from typing import Optional
from ccpragents.infrastructure.services.pr_diff_service import GitHubPRDiffService
from ccpragents.domain.entities.pr_diff import PRDiff


async def test_github_client():
    """Test GitHub client initialization and basic functionality."""

    print("Testing GitHub client initialization...")

    # Create the service
    service = GitHubPRDiffService()

    print("✓ GitHubPRDiffService created")

    # Test getting latest commit SHA
    try:
        result = await service.get_latest_commit_sha(
            "karcher-digital", "iotc-documentation", 42
        )

        if result:
            print(f"✓ Successfully got commit SHA: {result}")
        else:
            print("✗ Failed to get commit SHA (returned None)")
            print("This might indicate authentication issues or PR not found")

    except Exception as e:
        print(f"✗ Error getting commit SHA: {e}")

    # Test getting PR diff
    try:
        pr_diff_result: Optional[PRDiff] = await service.get_pr_diff(
            "karcher-digital", "iotc-documentation", 42
        )

        if pr_diff_result:
            print(f"✓ Successfully got PR diff: {type(pr_diff_result)}")
            print(
                f"  - Diff content length: {len(pr_diff_result.diff_content) if pr_diff_result.diff_content else 0}"
            )
            print(
                f"  - Commit messages: {len(pr_diff_result.commit_messages) if pr_diff_result.commit_messages else 0}"
            )
        else:
            print("✗ Failed to get PR diff (returned None)")

    except Exception as e:
        print(f"✗ Error getting PR diff: {e}")


if __name__ == "__main__":
    asyncio.run(test_github_client())
