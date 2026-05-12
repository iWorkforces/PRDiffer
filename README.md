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
git clone https://github.com/OCWorkforces/PRDifferMCP.git
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

```json
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
```

## AI Agent Skill

PRDifferMCP ships with an **[Agent Skill](https://skills.sh)** that teaches AI coding assistants how to use `prdiffer__get_pr_diff`, `prdiffer__approve_pr`, and `prdiffer__describe_pr` MCP tools effectively. The skill provides tool signatures, structured return type documentation, common workflows, error handling patterns, and constraints — so your AI agent can analyze PRs without guessing.

### Install the Skill

```bash
npx skills add OCWorkforces/PRDifferMCP
```

This installs the skill to all detected AI coding agents. For specific agents:

```bash
# Claude Code only
npx skills add OCWorkforces/PRDifferMCP -a claude-code

# OpenCode only
npx skills add OCWorkforces/PRDifferMCP -a opencode

# Multiple agents
npx skills add OCWorkforces/PRDifferMCP -a claude-code -a opencode -a cursor
```

### Supported Agents

The skill is compatible with **50+ AI coding agents** including:

| Agent | Install Flag | Skill Path |
|-------|-------------|------------|
| **Claude Code** | `claude-code` | `.claude/skills/` |
| **OpenCode** | `opencode` | `.agents/skills/` |
| **Cursor** | `cursor` | `.agents/skills/` |
| **Windsurf** | `windsurf` | `.windsurf/skills/` |
| **GitHub Copilot** | `github-copilot` | `.agents/skills/` |
| **Cline** | `cline` | `.agents/skills/` |
| **Gemini CLI** | `gemini-cli` | `.agents/skills/` |
| **Codex** | `codex` | `.agents/skills/` |

For a complete list, see [skills.sh](https://skills.sh).

### What the Skill Teaches Your Agent

After installation, your AI agent will know:

- **When to use each tool** — trigger phrases like "analyze this PR" or "approve this PR" activate the skill
- **Tool signatures** — exact parameter names, types, and whether they're required
- **Return types** — the structured `PRDiff` → `FileDiffResponse` → `FileStats` shape with field-level documentation
- **Error handling** — error codes (`E1001`, `E2002`, `E3001`, `E5002`) and recovery strategies
- **Common workflows** — analyze changes, review & approve, summarize & describe, extract statistics
- **Constraints** — URL format requirements, authentication, rate limiting, caching behavior

### How It Works

The skill's `SKILL.md` (located at `skills/prdiffer/SKILL.md`) activates automatically when your AI agent encounters trigger phrases like "get PR diff", "analyze pull request", or "approve this PR". The agent then uses the documented MCP tool signatures to call the PRDiffer server without guesswork.

The MCP server must still be running separately (`./start-prdiffer-mcp-server.sh`) — the skill only teaches the agent *how* to call the tools, not run them.

### Learn More

- **[skills.sh](https://skills.sh)** — Discover more agent skills
- **[skills/prdiffer/SKILL.md](skills/prdiffer/SKILL.md)** — Read the full skill definition
- **[Agent Skills Specification](https://agentskills.io)** — How skills work across agents
