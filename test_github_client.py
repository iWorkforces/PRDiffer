#!/usr/bin/env python3
"""Simple test script to verify GitHub client initialization and functionality."""

import asyncio
import os
from ccpragents.infrastructure.services.pr_diff_service import GitHubPRDiffService

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
        result = await service.get_pr_diff(
            "karcher-digital", "iotc-documentation", 42
        )

        if result:
            print(f"✓ Successfully got PR diff: {type(result)}")
            print(f"  - Repository: {result.repo_owner}/{result.repo_name}")
            print(f"  - PR Number: {result.pr_number}")
            print(f"  - Files: {len(result.files)}")
            print(f"  - Diff content length: {len(result.diff_content) if result.diff_content else 0}")
        else:
            print("✗ Failed to get PR diff (returned None)")

    except Exception as e:
        print(f"✗ Error getting PR diff: {e}")

if __name__ == "__main__":
    asyncio.run(test_github_client())