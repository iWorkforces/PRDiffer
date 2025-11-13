# CCPRAgentsMCP

🌾 🥳 🌋 🏰 🌅 🌕 Claude Code Github PR Agents MCP Server 🌖 🌔 🌈 🏆 👑

**MCP Server for GitHub PR Review Process with Full Contexts**

A powerful Model Context Protocol (MCP) server that provides AI assistants with comprehensive GitHub pull request analysis capabilities, including full-context diffs and detailed file change information.

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **Comprehensive PR Analysis**: Fetch complete pull request diffs with full file context
- 🚀 **Multiple Transport Modes**: Supports stdio, HTTP, SSE, and streamable HTTP transports
- 💾 **Smart Caching**: Commit-based caching with automatic invalidation
- 🔒 **Security First**: Input validation, sanitization, and protection against common attacks
- ⚡ **High Performance**: Parallel processing, request coalescing, and circuit breaker patterns
- 🎯 **Clean Architecture**: Domain-driven design with clear separation of concerns
- 🔧 **Flexible Configuration**: CLI arguments, environment variables, and configuration files

## Installation

### Install as MCP Tool (Recommended)

Install directly from GitHub using `uv`:

```bash
# Via HTTPS (recommended)
uv tool install ccpragents --force --from git+https://github.com/CCWorkforce/CCPRAgentsMCP.git

# Via SSH
uv tool install ccpragents --force --from git+ssh://git@github.com/CCWorkforce/CCPRAgentsMCP.git
```

### Install for Development

```bash
# Clone the repository
git clone https://github.com/CCWorkforce/CCPRAgentsMCP.git
cd CCPRAgentsMCP

# Install dependencies (requires Python 3.14+)
uv install

# Install development dependencies
uv install --dev
```

## Quick Start

### Using as MCP Tool (stdio mode)

After installation, the `ccpragents` command is available globally:

```bash
# Run with default stdio transport (for MCP clients)
ccpragents

# Show version
ccpragents --version

# Show help
ccpragents --help
```

### Using as HTTP Server

```bash
# Run as HTTP server on default port (9102)
ccpragents --transport http

# Run with custom port and host
ccpragents --transport http --port 9102 --host 0.0.0.0
```

### Using with Claude Code (Recommended)

The easiest way to add CCPRAgents to Claude Code is using the `claude mcp add` command:

```bash
# Add to current project (local scope - only available in this directory)
claude mcp add --transport stdio ccpragents http://127.0.0.1:9102/mcp

# Or add globally (user scope - available in all projects)
claude mcp add --transport http ccpragents http://127.0.0.1:9102/mcp
```

**Understanding Scopes:**
- **Local scope** (default): Server is only available in the current project directory
- **User scope** (`--scope user`): Server is available globally across all projects
- **Recommendation**: Use user scope if you'll analyze PRs from multiple repositories

**Note**: Replace `your_github_token` with your actual [GitHub Personal Access Token](https://github.com/settings/tokens).

**Verify installation:**
```bash
# List all MCP servers
claude mcp list

# Check if ccpragents is running (in Claude Code)
/mcp

# View ccpragents details
claude mcp get ccpragents
```

### Using with Claude Desktop

Alternatively, you can manually configure Claude Desktop by editing the configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ccpragents": {
      "command": "ccpragents",
      "env": {
        "GITHUB_TOKEN": "your-github-token-here"
      }
    }
  }
}
```

Replace `your-github-token-here` with your [GitHub Personal Access Token](https://github.com/settings/tokens).

## Authentication

CCPRAgents uses the `GITHUB_TOKEN` environment variable for GitHub API authentication. This provides secure access to GitHub repositories and higher API rate limits.

### Setting Up Authentication

**Option 1: Environment Variable** (Recommended for production)
```bash
export GITHUB_TOKEN="your_github_personal_access_token"
ccpragents
```

**Option 2: .env File** (Recommended for development)

Create a `.env` file in the project root:
```bash
GITHUB_TOKEN=your_github_personal_access_token
```

The `.env` file is already included in `.gitignore` and won't be committed to version control.

**Option 3: Claude Desktop Configuration**

Set the token in your Claude Desktop config (as shown in the Quick Start section above).

### Generating a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give your token a descriptive name
4. Select required scopes:
   - ✅ `repo` - Full control of private repositories
   - ✅ `read:org` - Read org and team membership
   - ✅ `read:user` - Read user profile data
5. Click "Generate token"
6. Copy the token immediately (you won't be able to see it again)
7. Set it as an environment variable or add to your `.env` file

### Security Best Practices

- **Never commit tokens** to version control
- **Use `.env` files** for local development (already gitignored)
- **Set environment variables** in production environments
- **Rotate tokens regularly** for enhanced security
- **Use minimal scopes** - only request the permissions you need

### Working Without Authentication

The server can run without a GitHub token but will be subject to strict API rate limits (60 requests per hour). For any serious use, authentication is strongly recommended.

## Managing the MCP Server

### List All MCP Servers

```bash
claude mcp list
```

This shows all configured MCP servers with their scope (local/user) and status.

### View Server Details

```bash
# Get detailed information about ccpragents
claude mcp get ccpragents
```

### Update Server Configuration

```bash
# Update environment variables
claude mcp update ccpragents --env GITHUB_TOKEN=new_token

# Change scope
claude mcp update ccpragents --scope user
```

### Remove the Server

```bash
# Remove from current project
claude mcp remove ccpragents

# Remove from user scope
claude mcp remove ccpragents --scope user
```

### Check Server Status in Claude Code

In Claude Code, you can verify the MCP server is running by typing:

```
/mcp
```

This displays all active MCP servers and their available tools.

### Troubleshooting

**Connection Issues:**
- Ensure `ccpragents` is installed: `uv tool list | grep ccpragents`
- Verify `GITHUB_TOKEN` is set: `echo $GITHUB_TOKEN`
- Restart Claude Code after configuration changes
- Check logs with: `claude mcp logs ccpragents`

**Server Not Listed:**
- Confirm scope matches: local servers only appear in specific projects
- User-scoped servers are available globally
- Re-add the server with the correct scope if needed

### Using in Claude Code

Once configured, you can analyze GitHub PRs directly in Claude Code:

**Example prompts:**

```
Analyze the changes in https://github.com/owner/repo/pull/123
```

```
Review this PR for potential bugs: https://github.com/owner/repo/pull/456
```

```
Summarize the key changes in https://github.com/owner/repo/pull/789
```

The `get_pr_diff` tool will automatically be invoked to fetch comprehensive diff information, including:
- Complete file changes with full context
- Commit messages and metadata
- Addition/deletion statistics
- File-by-file analysis

## Configuration

### Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (required for private repos)
- `MCP_TRANSPORT`: Transport mode (stdio, http, sse, streamable-http)
- `MCP_PORT`: Server port for non-stdio transports
- `MCP_HOST`: Server host for non-stdio transports
- `MCP_PATH`: Server path for non-stdio transports

### Configuration File

The server uses `settings.toml` for detailed configuration. See the file for all available options including:

- GitHub API settings (rate limits, retries, timeouts)
- File filtering patterns
- Caching configuration
- Parallel processing settings
- Circuit breaker and retry strategies

### CLI Arguments

```bash
ccpragents [OPTIONS]

Options:
  --version              Show version and exit
  --transport TEXT       Transport protocol [stdio|http|sse|streamable-http]
  --port INTEGER         Server port (default: 9102)
  --host TEXT            Server host (default: 127.0.0.1)
  --path TEXT            Server path (default: /mcp)
  --help                 Show help message
```

### Configuration Priority

Settings are applied in the following order (highest to lowest priority):

1. CLI arguments (`--transport`, `--port`, etc.)
2. Environment variables (`MCP_TRANSPORT`, `MCP_PORT`, etc.)
3. Settings file (`settings.toml`)
4. Built-in defaults

## Usage

### MCP Tool: `get_pr_diff`

The server exposes a single MCP tool for fetching PR diff information:

**Input:**
- `pr_url`: Full GitHub PR URL (e.g., `https://github.com/owner/repo/pull/123`)

**Output:**
- Complete PR diff data including:
  - Commit messages
  - File changes with full context diffs
  - Addition/deletion statistics
  - File metadata (status, patches)

**Example with MCP Client:**

```python
from mcp import Client

async with Client("ccpragents") as client:
    result = await client.call_tool("get_pr_diff", {
        "pr_url": "https://github.com/owner/repo/pull/123"
    })
    print(result)
```

### Manual Server Execution

For development or testing:

```bash
# Run via uv (with dependencies)
uv run python ccpragents/server.py

# Or after installation
python -m ccpragents.server
```

## Development

### Running Tests

```bash
# Run all tests
./start-unittest.sh --run

# Run with coverage
./start-unittest.sh --coverage

# Run in parallel
./start-unittest.sh --parallel
```

### Code Quality

```bash
# Lint code
./start-lint.sh --check

# Auto-fix issues
./start-lint.sh --fix

# Format code
./start-lint.sh --format
```

### Type Checking

```bash
# Run type checking
./start-type-check.sh --check

# With coverage report
./start-type-check.sh --coverage
```

## Architecture

CCPRAgents follows Clean Architecture principles with three main layers:

### Domain Layer
- Core business entities (PRDiff, FilePatchInfo)
- Use cases (GetPRDiffUseCase)
- Repository and service interfaces
- No external dependencies

### Application Layer
- FastMCP server implementation
- Tool registration and request handling
- Component orchestration

### Infrastructure Layer
- GitHub API integration
- Caching and settings services
- Security validation
- Logging and utilities

## Security

The server implements comprehensive security measures:

- ✅ Input validation for all user-provided data
- ✅ Protection against command injection, path traversal, and SQL injection
- ✅ GitHub URL validation with strict pattern matching
- ✅ Safe logging to prevent log injection
- ✅ Rate limiting and timeout protection

## Performance

Optimized for handling large PRs:

- **Parallel Processing**: Concurrent file processing using task groups
- **Request Coalescing**: Deduplicates simultaneous requests for the same resource
- **Smart Caching**: Commit-based caching with automatic invalidation
- **Circuit Breaker**: Prevents cascading failures
- **Adaptive Retry**: Context-aware retry strategies with exponential backoff

## Troubleshooting

### Common Issues

**Issue**: `ccpragents: command not found`
- **Solution**: Ensure `uv tool install` completed successfully and your PATH includes uv tool binaries

**Issue**: GitHub API rate limiting
- **Solution**: Set `GITHUB_TOKEN` environment variable with a valid GitHub token

**Issue**: Python version error
- **Solution**: This package requires Python 3.14+. Update your Python installation.

**Issue**: Transport connection errors
- **Solution**: Check firewall settings and ensure the specified port is available

### Debug Mode

Enable debug logging by adding an environment override to `settings.toml`:

```toml
# Example: Add this section to enable debug mode for development environment
[development]
app.debug = true
app.log_level = "DEBUG"
```

Then set `ENV_FOR_DYNACONF=development` when running the server.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run linting and type checking
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Links

- **Repository**: https://github.com/CCWorkforce/CCPRAgentsMCP
- **Issues**: https://github.com/CCWorkforce/CCPRAgentsMCP/issues
- **Model Context Protocol**: https://modelcontextprotocol.io

## Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - FastAPI-based MCP server framework
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API v3 client
- [Dynaconf](https://www.dynaconf.com/) - Configuration management
- [anyio](https://github.com/agronholm/anyio) - Async compatibility layer

---

**Made with ❤️ by CCWorkforce Engineers**
