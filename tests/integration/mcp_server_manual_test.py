# https://github.com/jlowin/fastmcp?tab=readme-ov-file#mcp-clients
# https://github.com/StevenBtw/uv-docs-mcp/blob/main/src/uv_docs/server.py
from fastmcp import Client
import anyio
from fastmcp.client.client import CallToolResult


async def main():
    # Connect via stdio to a local script
    async with Client("http://127.0.0.1:9102/mcp") as client:
        tools = await client.list_tools()
        print(f"Available tools: {tools}")
        result: CallToolResult = await client.call_tool(
            "get_pr_diff",
            {"pr_url": "https://github.com/CCWorkforce/CCPRAgentsMCP/pull/8"},
        )
        print(f"Result: {result.content}")


if __name__ == "__main__":
    anyio.run(main)
