# PRDifferMCP

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)](https://github.com/yourusername/CCPRAgentsMCP)

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

# Run type checking (strict mode)
uv run pyright prdiffer

# Run type checking for tests (relaxed mode)
uv run pyright tests

# Run tests
./start-unittest.sh --run

# Run tests with coverage
./start-unittest.sh --coverage
```

### Type Checking Standards

This project uses **Pyright** in strict mode for production code with the following standards:

- **Production code** (`prdiffer/`): Strict type checking enabled
- **Test code** (`tests/`): Standard type checking with relaxed unknown type warnings

#### Type Annotation Guidelines

1. **All functions must have return type annotations**
2. **Use TypedDict for dictionary types** when the structure is known
3. **Avoid `Any` type** - use proper types or `object` when truly generic
4. **Use Protocol for interfaces** instead of ABC for better dataclass compatibility
5. **Add type arguments to generic containers** (e.g., `dict[str, Any]` not just `dict`)

#### Running Type Checks

```bash
# Check production code (strict mode)
uv run pyright prdiffer

# Check all code including tests
uv run pyright

# Generate type stubs (if needed)
pyright --verifytypes prdiffer
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
host = "127.0.0.1"
path = "/mcp"

[default.github]
github_token = ""
rate_limit = 5000
timeout = 30
ignore_patterns = ["*.lock", "node_modules/"]
valid_extensions = [".py", ".js", ".ts", ".md"]

# Metrics and monitoring
[metrics]
enabled = true  # Enable metrics tracking
prometheus_enabled = false  # Use Prometheus format
include_stages = false  # Include stage-level timing

# Webhook configuration
github.webhook_secret = ""  # GitHub webhook secret for HMAC verification
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

### HTTP Endpoints

The server exposes HTTP endpoints for monitoring and integration:

- **GET /metrics**: Prometheus-formatted metrics including request counts, execution times, success rates, and system health. Requires `metrics.enabled=true` in settings.toml.
- **POST /webhook**: GitHub webhook endpoint for cache invalidation. Requires HMAC signature verification with `GITHUB_WEBHOOK_SECRET` environment variable. Supported events: `push`, `pull_request` (opened, synchronize, reopened).

### Streamable-HTTP Deployment

For production deployments using streamable-http mode, configure a reverse proxy (nginx, Apache, Caddy) to add security headers:

```nginx
location /mcp {
    proxy_pass http://localhost:9102;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Content-Security-Policy "default-src 'self'";
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Content-Security-Policy and HSTS
    add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'self'";
    add_header Content-Security-Policy "upgrade-insecure-requests";
    
    # Referrer
    add_header Referrer-Policy: strict-origin-when-cross-origin;
}
```

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
