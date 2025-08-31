# CCPRAgents MCP Server Usage Guide

## Starting the Server

The easiest way to start the CCPRAgents MCP server is using the provided startup script:

```bash
./start-ccpragents-mcp-server.sh
```

This script will:
- Check for required dependencies (uv)
- Verify the project structure
- Start the server with proper configuration
- Handle graceful shutdown when stopped (Ctrl+C)

**Command executed by the script:**
```bash
uv run python ccpragents/server.py --link-mode=copy
```

## Server Configuration

### Default Configuration
- **Transport**: HTTP
- **Port**: 9101
- **Link Mode**: copy

### Custom Configuration
You can modify the server configuration using environment variables:

```bash
# Change transport mode (http, sse, streamable-http, stdio)
TRANSPORT=sse ./start-ccpragents-mcp-server.sh

# Change port
PORT=9102 ./start-ccpragents-mcp-server.sh
```

## Accessing the MCP Server

Once running, you can interact with the MCP server through various endpoints:

### HTTP Endpoint
Access the MCP server HTTP interface at:
```
http://127.0.0.1:9101/mcp
```

If running on a custom port (e.g., 9102):
```
http://127.0.0.1:9102/mcp
```

### Configuration Options
- `TRANSPORT`: Server transport mode (`http`, `sse`, `streamable-http`, `stdio`)
- `PORT`: Server port (default: 9101)
- `GITHUB_TOKEN`: Optional GitHub authentication token

### Transport Modes
- **http**: HTTP server mode (default)
- **sse**: Server-sent events
- **streamable-http**: FastMCP streamable HTTP
- **stdio**: Standard input/output (for MCP clients)

## Prerequisites
- Python 3.13+
- uv package manager (install from: https://docs.astral.sh/uv/getting-started/installation/)

## Development Workflow

### Environment Setup
```bash
# Install dependencies
uv install

# Install development dependencies
uv install --dev
```

### Running Tests
```bash
# Basic server test
uv run python tests/test_mcp_server.py
```

### Code Quality
```bash
# Lint code
./start-lint.sh --check

# Auto-fix linting issues
./start-lint.sh --fix

# Format code
./start-lint.sh --format
```

### Configuration Summary

  The created mcp-config.json contains:

  {
    "mcpServers": {
      "ccpragents": {
        "command": "uv",
        "args": ["run", "python", "ccpragents/server.py"],
        "env": {
          "PORT": "9102",
          "TRANSPORT": "http"
        }
      }
    }
  }

  How to Use This Configuration

  For Claude Desktop:
  1. Copy the contents of mcp-config.json to your Claude Desktop configuration file:
    - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
    - Windows: %APPDATA%\Claude\claude_desktop_config.json

  For Claude Code:
  claude mcp add --transport http ccpragents http://127.0.0.1:9102/mcp

  For other MCP clients:
  - Use the JSON structure from mcp-config.json
  - Ensure your MCP server is running with HTTP transport
  - Point to the /mcp endpoint

  The configuration will allow MCP clients to discover and use the PR diff analysis tools provided by your CCPRAgents server. Make sure your server is running on port 9102 when using this configuration.