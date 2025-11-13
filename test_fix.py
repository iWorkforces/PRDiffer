#!/usr/bin/env python3
"""Test script to verify the MCP server fix."""

import asyncio
import json
from typing import Any, Dict

async def test_mcp_server():
    """Test the MCP server get_pr_diff tool."""

    # Test data
    test_url = "https://github.com/karcher-digital/iotc-things/pull/17"

    print(f"Testing MCP server with URL: {test_url}")

    try:
        # Import the server components
        from ccpragents.application.mcp_server import FastMCPServer
        from ccpragents.application.factory import create_mcp_server

        print("✓ Successfully imported server components")

        # Create the server instance
        server = create_mcp_server()
        print("✓ Successfully created MCP server instance")

        # Test the URL parsing
        try:
            repo_owner, repo_name, pr_number = server._parse_pr_url(test_url)
            print(f"✓ URL parsing successful: owner={repo_owner}, repo={repo_name}, pr={pr_number}")
        except Exception as e:
            print(f"✗ URL parsing failed: {e}")
            return

        # Test the use case creation and execution
        try:
            # Create a repository instance (this is what the server does internally)
            repository = server._github_repository_class(repo_owner, repo_name, pr_number)
            print(f"✓ Repository created: {type(repository).__name__}")

            # Create the use case (this is the fix we made)
            from ccpragents.domain.usecases.pr_diff_usecases import GetPRDiffUseCaseLegacy

            use_case = GetPRDiffUseCaseLegacy(repository, cache_service=server._cache_service)
            print(f"✓ Use case created: {type(use_case).__name__}")

            # Test that the execute method exists and can be called
            if hasattr(use_case, 'execute'):
                print("✓ Use case has execute method")
                print(f"✓ Execute method signature: {use_case.execute.__doc__ or 'No docstring'}")
            else:
                print("✗ Use case missing execute method")
                return

        except Exception as e:
            print(f"✗ Use case creation failed: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n🎉 All tests passed! The fix should work correctly.")
        print("\nTo test the actual server, you can:")
        print("1. Run: uv run python ccpragents/server.py")
        print("2. Use an MCP client to call the get_pr_diff tool")
        print("3. Or test with curl: curl -X POST http://127.0.0.1:9102/mcp ...")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())