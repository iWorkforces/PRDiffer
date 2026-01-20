# PRDifferMCP

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.7-orange.svg)](https://github.com/yourusername/CCPRAgentsMCP)

A Model Context Protocol (MCP) server that provides comprehensive GitHub Pull Request diff analysis with full file context for AI assistants and code review tools.

## Overview

PRDifferMCP is an MCP server that extracts and analyzes GitHub PR diffs, providing AI assistants with rich context for code review, analysis, and assistance. Unlike standard diff tools that only show changed hunks, PRDifferMCP provides full-file context, commit messages, and intelligent file filtering.

### Key Features

- **Full-File Context Diffs**: See entire files with changes, not just hunks
- **Commit Message Integration**: Access PR commit history and messages
- **Intelligent File Filtering**: Pattern-based filtering to focus on relevant files
- **Smart Caching**: Commit-based cache invalidation ensures fresh data with optimal performance
- **Security First**: Comprehensive input validation, rate limiting, and authentication support
- **Multiple Transport Modes**: Support for stdio, HTTP, SSE, and streamable-HTTP
- **Async Architecture**: Built with anyio for efficient concurrent processing
- **Clean Architecture**: Domain-driven design with clear separation of concerns

## Quick Start

### Prerequisites

- Python 3.14 or higher
- `uv` package manager (recommended) or pip
- GitHub Personal Access Token (for authenticated requests)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/CCPRAgentsMCP.git
cd CCPRAgentsMCP

# Install dependencies with uv (recommended)
uv install

# Or with pip
pip install -e .
```

### Basic Usage

1. Set your GitHub token (recommended for higher rate limits):

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

2. Start the MCP server:

```bash
uv run python prdiffer/server.py
```

3. The server will start on the default port (9102) with HTTP transport:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9102
```

### Example Request

```python
import httpx

async def get_pr_diff():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:9102/mcp/tools/get_pr_diff",
            json={
                "pr_url": "https://github.com/owner/repo/pull/123"
            }
        )
        result = response.json()
        print(result["content"])
```

## Documentation

- **[Usage Guide](USAGE.md)** - Comprehensive usage instructions and examples
- **[Security Guide](SecurityUsageGuide.md)** - Authentication, API keys, and security best practices
- **[Development Plan](docs/development-plan.md)** - Current development roadmap
- **[Implementation Plan](docs/implementation-plan.md)** - Detailed task breakdown and status

## Development

### Setup Development Environment

```bash
# Install development dependencies
uv install --dev

# Run linting
./start-lint.sh --all

# Run type checking
./start-type-check.sh --check

# Run tests
./start-unittest.sh --run

# Run tests with coverage
./start-unittest.sh --coverage
```

### Project Structure

```
CCPRAgentsMCP/
├── prdiffer/
│   ├── domain/           # Business logic and entities
│   ├── application/      # MCP server and components
│   └── infrastructure/   # External service integrations
├── tests/                # Test suite
├── docs/                 # Documentation
├── settings.toml         # Configuration
└── prdiffer/server.py    # Server entry point
```

### Configuration

The server is configured via `settings.toml`. Key configuration options:

```toml
[mcp]
transport = "http"        # stdio, http, sse, streamable-http
port = 9102
host = "0.0.0.0"

[github]
rate_limit = 5000
timeout = 30
max_retries = 3

[auth]
enabled = true            # Enable authentication
api_keys = []             # Configure via environment
```

### Architecture

PRDifferMCP follows **Clean Architecture** principles with clear layer separation:

- **Domain Layer**: Pure business logic with no external dependencies
- **Infrastructure Layer**: GitHub API, caching, security, utilities
- **Application Layer**: MCP server, components, and orchestration

For detailed architecture documentation, see `CLAUDE.md`.

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Code Style**: Follow the existing code style (use `./start-lint.sh --format`)
2. **Tests**: Write tests for new features (aim for >85% coverage)
3. **Documentation**: Update relevant documentation
4. **Commits**: Use descriptive commit messages with conventional commits format
5. **PRs**: Describe changes clearly and link to related issues

### Development Workflow

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes and test
./start-lint.sh --all
./start-unittest.sh --run
./start-type-check.sh --check

# Commit with conventional commits
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature-name
```

## Security

PRDifferMCP takes security seriously:

- **Input Validation**: All inputs validated against injection attacks
- **Authentication**: API key-based authentication with SHA-256 hashing
- **Rate Limiting**: Configurable per-client rate limiting
- **Safe Logging**: Sensitive data sanitized before logging
- **HTTPS Support**: TLS/SSL for secure communications

See [SecurityUsageGuide.md](SecurityUsageGuide.md) for detailed security information.

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | - |
| `MCP_TRANSPORT` | Server transport mode | `http` |
| `MCP_PORT` | Server port | `9102` |
| `MCP_HOST` | Server host | `0.0.0.0` |
| `MCP_AUTH_ENABLED` | Enable authentication | `true` |
| `MCP_API_KEYS` | Comma-separated API keys | - |

### Transport Modes

- **stdio**: Standard input/output (default for MCP clients)
- **http**: HTTP server mode
- **sse**: Server-sent events
- **streamable-http**: FastMCP streamable HTTP

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/CCPRAgentsMCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/CCPRAgentsMCP/discussions)
- **Documentation**: See the [docs](docs) directory

## Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API client
- [anyio](https://github.com/agronholm/anyio) - Async compatibility layer
- [Dynaconf](https://github.com/dynaconf/dynaconf) - Configuration management

---

**Version**: 0.4.7
**Last Updated**: 2026-01-20
