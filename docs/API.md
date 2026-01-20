# API Documentation

**Version:** 0.4.7
**Last Updated:** 2026-01-20

## Overview

PRDifferMCP provides a Model Context Protocol (MCP) server with tools for GitHub Pull Request diff analysis. This document describes all available MCP tools, request/response formats, error codes, and usage examples.

---

## Table of Contents

1. [Server Connection](#server-connection)
2. [Authentication](#authentication)
3. [Available Tools](#available-tools)
4. [Request/Response Format](#requestresponse-format)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)
7. [Code Examples](#code-examples)

---

## Server Connection

### Transport Modes

The MCP server supports multiple transport protocols:

| Transport | Description | Default Port | Use Case |
|-----------|-------------|--------------|----------|
| `stdio` | Standard input/output | - | MCP client communication |
| `http` | HTTP server | 9102 | Web clients, REST API |
| `sse` | Server-Sent Events | 9102 | Real-time updates |
| `streamable-http` | FastMCP streamable HTTP | 9102 | Streaming responses |

### Connection Endpoints

```
HTTP:     http://localhost:9102/mcp
SSE:      http://localhost:9102/mcp
Stdio:    Standard input/output
```

### Environment Configuration

```bash
export MCP_TRANSPORT=http    # Transport mode
export MCP_PORT=9102         # Server port
export MCP_HOST=127.0.0.1    # Server host
```

---

## Authentication

### API Key Authentication

When authentication is enabled (default: `true`), clients must provide a valid API key.

#### Headers

```http
X-API-Key: your-api-key-here
```

or

```http
Authorization: Bearer your-api-key-here
```

#### Configuration

```bash
# Enable authentication (default)
export MCP_AUTH_ENABLED=true

# Set API keys (comma-separated)
export MCP_API_KEYS="key1,key2,key3"

# Set admin API key
export MCP_ADMIN_API_KEY="admin-key"
```

#### JWT Token Support

For JWT-based authentication, configure:

```bash
export MCP_JWT_SECRET="your-jwt-secret-key"
```

JWT tokens must be signed with the configured secret and include valid claims.

---

## Available Tools

### get_pr_diff

Retrieves comprehensive pull request diff analysis with full file context.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_url` | string | Yes | Full GitHub PR URL |
| `api_key` | string | No* | API key for authentication |

*Required when authentication is enabled.

#### Request Format

```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "api_key": "your-api-key"
}
```

#### Response Format

Success response (200 OK):

```json
{
  "content": {
    "diff_content": "Full diff content for all files...",
    "commit_messages": "# PR Title\\n\\n## Commit Messages\\n\\n1. abc123 - Initial commit\\n2. def456 - Add feature",
    "files_changed": 5,
    "total_additions": 150,
    "total_deletions": 50,
    "generation_metadata": {
      "cache_hit": false,
      "commit_sha": "abc123def456",
      "generation_time_ms": 1234,
      "files_analyzed": 5,
      "timestamp": "2026-01-20T12:00:00Z"
    },
    "file_summaries": [
      {
        "filename": "src/main.py",
        "additions": 50,
        "deletions": 10,
        "changes": 60,
        "patch": "--- a/src/main.py\\n+++ b/src/main.py\\n@@ -1,5 +1,10 @@..."
      }
    ]
  },
  "isError": false
}
```

#### URL Format

The PR URL must match the following pattern:

```
https://github.com/{owner}/{repo}/pull/{pr_number}
```

**Example:**
```
https://github.com/PyGithub/PyGithub/pull/2000
```

#### Security Validations

The following security validations are performed:

- **URL Format**: Must match GitHub PR URL pattern
- **Repository Validation**: Owner and repo names validated (max 39/100 chars, alphanumeric)
- **PR Number**: Must be positive integer (max 1,000,000)
- **Injection Detection**: Blocks command injection, SQL injection, path traversal
- **Length Limits**: URL max 2000 characters

---

## Request/Response Format

### MCP Tool Call Request

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_pr_diff",
    "arguments": {
      "pr_url": "https://github.com/owner/repo/pull/123"
    }
  }
}
```

### Success Response

```json
{
  "result": {
    "content": [PRDiff data],
    "isError": false
  }
}
```

### Error Response

```json
{
  "result": {
    "content": "Error message",
    "isError": true
  },
  "error": {
    "code": "E4001",
    "message": "Invalid URL format"
  }
}
```

---

## Error Codes

### Input Validation Errors (E1xxx)

| Code | Message | Description |
|------|---------|-------------|
| E1001 | Invalid URL format | URL does not match GitHub PR pattern |
| E1002 | Invalid repository identifier | Owner or repo name invalid |
| E1003 | Invalid PR number | PR number must be positive integer |
| E1004 | Suspicious operation detected | Potential security threat detected |
| E1005 | Input sanitization failed | Input contains invalid characters |
| E1006 | Missing required parameter | Required parameter not provided |

### Authentication Errors (E2xxx)

| Code | Message | Description |
|------|---------|-------------|
| E2001 | Authentication required | API key required but not provided |
| E2002 | Invalid API key | Provided API key is invalid |
| E2003 | Token expired | JWT token has expired |
| E2004 | Invalid token signature | JWT signature verification failed |
| E2005 | Account locked | Too many failed attempts |
| E2006 | Invalid token format | Token format is invalid |

### Rate Limiting Errors (E3xxx)

| Code | Message | Description |
|------|---------|-------------|
| E3001 | Rate limit exceeded | Too many requests |
| E3002 | Rate limit reset in {seconds} | Time until rate limit resets |

### Not Found Errors (E4xxx)

| Code | Message | Description |
|------|---------|-------------|
| E4001 | Repository not found | Repository does not exist |
| E4002 | Pull request not found | PR does not exist |
| E4003 | Branch not found | Specified branch does not exist |

### Internal Errors (E5xxx)

| Code | Message | Description |
|------|---------|-------------|
| E5001 | Internal server error | Unexpected server error |
| E5002 | GitHub API error | Error calling GitHub API |
| E5003 | Cache error | Cache operation failed |
| E5004 | Timeout error | Request timed out |

---

## Rate Limiting

### Per-Client Rate Limits

Rate limiting is enforced per authenticated client or per IP address (when auth is disabled).

**Default Limits:**
- **Requests per minute**: 100
- **Burst size**: 20

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705768800
```

### Rate Limit Response

When rate limit is exceeded:

```json
{
  "error": {
    "code": "E3001",
    "message": "Rate limit exceeded. Try again in 30 seconds."
  }
}
```

### Configuration

```toml
[rate_limiting]
requests_per_minute = 100
burst_size = 20
```

---

## Code Examples

### Python

#### Using HTTP with httpx

```python
import httpx
import asyncio

async def get_pr_diff(pr_url: str, api_key: str = None):
    """Get PR diff using HTTP."""
    url = "http://localhost:9102/mcp/tools/get_pr_diff"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={"pr_url": pr_url, "api_key": api_key},
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

# Usage
result = asyncio.run(get_pr_diff(
    "https://github.com/owner/repo/pull/123",
    api_key="your-api-key"
))
print(result["content"]["diff_content"])
```

#### Using MCP Client SDK

```python
from mcp import Client

async def get_pr_diff_with_mcp(pr_url: str):
    """Get PR diff using MCP client."""
    async with Client("http://localhost:9102/mcp") as client:
        result = await client.call_tool("get_pr_diff", {
            "pr_url": pr_url
        })
        return result

# Usage
result = asyncio.run(get_pr_diff_with_mcp(
    "https://github.com/owner/repo/pull/123"
))
```

### TypeScript

#### Using fetch API

```typescript
interface PRDiffResponse {
  content: {
    diff_content: string;
    commit_messages: string;
    files_changed: number;
    total_additions: number;
    total_deletions: number;
    generation_metadata: {
      cache_hit: boolean;
      commit_sha: string;
      generation_time_ms: number;
      files_analyzed: number;
      timestamp: string;
    };
    file_summaries: Array<{
      filename: string;
      additions: number;
      deletions: number;
      changes: number;
      patch: string;
    }>;
  };
  isError: boolean;
}

async function getPRDiff(
  prUrl: string,
  apiKey?: string
): Promise<PRDiffResponse> {
  const response = await fetch('http://localhost:9102/mcp/tools/get_pr_diff', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey && { 'X-API-Key': apiKey }),
    },
    body: JSON.stringify({
      pr_url: prUrl,
      ...(apiKey && { api_key: apiKey }),
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Usage
const result = await getPRDiff(
  'https://github.com/owner/repo/pull/123',
  'your-api-key'
);
console.log(result.content.diff_content);
```

### cURL

```bash
# Basic request
curl -X POST http://localhost:9102/mcp/tools/get_pr_diff \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'

# With authentication
curl -X POST http://localhost:9102/mcp/tools/get_pr_diff \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'

# With Bearer token
curl -X POST http://localhost:9102/mcp/tools/get_pr_diff \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'

# Pretty print JSON response
curl -X POST http://localhost:9102/mcp/tools/get_pr_diff \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}' | jq
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

async function getPRDiff(prUrl, apiKey) {
  try {
    const response = await axios.post(
      'http://localhost:9102/mcp/tools/get_pr_diff',
      {
        pr_url: prUrl,
        ...(apiKey && { api_key: apiKey }),
      },
      {
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey && { 'X-API-Key': apiKey }),
        },
        timeout: 30000,
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    throw error;
  }
}

// Usage
getPRDiff(
  'https://github.com/owner/repo/pull/123',
  'your-api-key'
)
  .then(result => {
    console.log(result.content.diff_content);
  })
  .catch(error => {
    console.error('Failed to get PR diff:', error);
  });
```

---

## Response Envelope Structure

All responses follow a standard envelope format:

```json
{
  "content": {
    "diff_content": "string - Full diff content",
    "commit_messages": "string - Formatted commit messages",
    "files_changed": "number - Number of files changed",
    "total_additions": "number - Total lines added",
    "total_deletions": "number - Total lines deleted",
    "generation_metadata": {
      "cache_hit": "boolean - Whether cache was used",
      "commit_sha": "string - Latest commit SHA",
      "generation_time_ms": "number - Time to generate diff",
      "files_analyzed": "number - Number of files analyzed",
      "timestamp": "string - ISO 8601 timestamp"
    },
    "file_summaries": [
      {
        "filename": "string - File path",
        "additions": "number - Lines added",
        "deletions": "number - Lines deleted",
        "changes": "number - Total changes",
        "patch": "string - Full patch"
      }
    ]
  },
  "isError": "boolean - Whether an error occurred"
}
```

---

## Best Practices

1. **Always validate URLs** before sending to the API
2. **Handle rate limits** gracefully using the provided headers
3. **Use caching** - the server caches results by commit SHA
4. **Check for errors** using the `isError` field
5. **Set appropriate timeouts** - large PRs may take longer
6. **Use authentication** in production environments
7. **Monitor rate limit headers** to avoid being throttled

---

## Support

For issues, questions, or contributions:
- **Issues**: [GitHub Issues](https://github.com/CCWorkforce/PRDifferMCP/issues)
- **Documentation**: [docs/](../)
- **Security**: See [SecurityUsageGuide.md](../SecurityUsageGuide.md)

---

*Last Updated: 2026-01-20*
