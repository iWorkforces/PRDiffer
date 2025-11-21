# CCPRAgents MCP Server Usage Guide

## Starting the Server

The easiest way to start the CCPRAgents MCP server is using the provided startup script:

```bash
export GITHUB_TOKEN=ghp_xxx
```

```bash
./start-ccpragents-mcp-server.sh
```

## Accessing the MCP Server

Once running, you can interact with the MCP server through various endpoints:

### HTTP Endpoint
Access the MCP server HTTP interface at:
```
http://127.0.0.1:9102/mcp
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

#### Add to Claude Code

```bash
claude mcp add --transport http ccpragents http://127.0.0.1:9102/mcp
```
