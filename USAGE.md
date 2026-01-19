# PRDiffer MCP Server Usage Guide

## Starting the Server

The easiest way to start the PRDiffer MCP server is using the provided startup script:

```bash
export GITHUB_TOKEN=ghp_xxx
```

```bash
./start-prdiffer-mcp-server.sh
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
      "prdiffer": {
        "command": "uv",
        "args": ["run", "python", "prdiffer/server.py"],
        "env": {
          "PORT": "9102",
          "TRANSPORT": "http"
        }
      }
    }
  }

#### Add to Claude Code

```bash
claude mcp add --transport http prdiffer http://127.0.0.1:9102/mcp
```

## Optional Settings

You can tune file processing and diff output via `settings.toml`:

- `file_processing.concurrent_downloads`: Max workers for parallel file fetching.
- `file_processing.parallel_fetch_threshold`: File count threshold to enable parallel fetching.
- `diff.truncate_enabled`: Enable/disable diff truncation.
- `diff.max_total_chars`: Max diff size before truncation.
- `diff.truncation_notice`: Marker appended when diff is truncated.
