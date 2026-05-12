# PRDifferMCP

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

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
git clone https://github.com/CCWorkforce/PRDifferMCP.git
cd PRDifferMCP

# Install dependencies with uv (recommended)
uv install

# Or with pip
pip install -e .
```

### Basic Usage

1. Set your GitHub token:

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

2. Start the MCP server:

```bash
./start-prdiffer-mcp-server.sh
```

### Accessing the MCP Server

#### Add to Claude Code

```bash
claude mcp add --transport http prdiffer http://127.0.0.1:9102/mcp
```

#### Add to OpenCode

File `opencode.json`:

{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "prdiffer": {
      "type": "remote",
      "url": "http://127.0.0.1:9102/mcp",
      "enabled": true
    }
  }
}
