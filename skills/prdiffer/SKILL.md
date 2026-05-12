---
name: prdiffer
description: "This skill should be used when the user asks to 'get PR diff', 'fetch pull request changes', 'analyze PR', 'review pull request', 'check what changed in a PR', 'approve PR', 'approve pull request', 'describe PR', 'update PR description', or needs to interact with GitHub pull requests via the PRDifferMCP server. Trigger phrases include 'get pr diff', 'fetch diff', 'pr changes', 'pull request analysis', 'what files changed', 'approve this pr', 'describe the pr'."
---

# PRDiffer - GitHub PR Diff Analysis via MCP

PRDifferMCP exposes MCP tools for fetching structured GitHub PR diff data, approving PRs, and updating PR descriptions. The tools are prefixed with `prdiffer__` in the MCP namespace.

## Prerequisites

A running PRDifferMCP server is required. The server must be configured in the agent's MCP settings:

```json
{
  "mcp": {
    "prdiffer": {
      "type": "remote",
      "url": "http://127.0.0.1:9102/mcp",
      "enabled": true
    }
  }
}
```

If authentication is enabled on the server, pass the `api_key` parameter to each tool call.

---

## Tools

### prdiffer__get_pr_diff

Fetch the structured file-level diff for a GitHub pull request. This is the primary tool for PR analysis.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_url` | `string` | Yes | Full GitHub PR URL: `https://github.com/{owner}/{repo}/pull/{number}` |
| `api_key` | `string` | No | API key for authentication (required if server auth is enabled) |

**Returns:** `PRDiff` object:

```
PRDiff {
  files: FileDiffResponse[]   // Array of changed files
}
```

Each `FileDiffResponse` contains:

```
FileDiffResponse {
  path: string                // File path (e.g., "src/main.py")
  status: EDIT_TYPE           // One of: "added", "deleted", "modified", "renamed", "unknown"
  stats: FileStats {
    additions: int             // Lines added
    deletions: int             // Lines deleted
  }
  diff: string                 // Full unified diff/patch content for this file
}
```

**Errors:**

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `E1001_INVALID_URL` | Malformed PR URL or missing parameter | Reconstruct URL from owner/repo/number components |
| `E1001_INVALID_URL` | Invalid repository or PR number | Verify the repository exists and the PR number is correct |
| `E2002_AUTH_FAILED` | Missing or invalid API key | Provide valid `api_key` parameter |
| `E3001_RATE_LIMITED` | Request rate limit exceeded | Wait and retry; implement exponential backoff |
| `E5002_GITHUB_API_ERROR` | GitHub API failure or PR not found | Verify repository access and PR existence |

**Example:**

```
// Fetch diff for a PR
result = prdiffer__get_pr_diff(
  pr_url="https://github.com/owner/repo/pull/42"
)

// Iterate changed files
for file in result.files:
  print(file.path)       // "src/auth/login.py"
  print(file.status)     // "modified"
  print(file.stats.additions)  // 25
  print(file.stats.deletions)  // 10
  print(file.diff)        // Full unified diff content
```

---

### prdiffer__approve_pr

Approve a GitHub PR with an encouraging comment.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_url` | `string` | Yes | Full GitHub PR URL |
| `compliment` | `string` | Yes | Compliment text to include in the approval review |
| `api_key` | `string` | No | API key for authentication |

**Returns:** `string` - Success confirmation message.

**Example:**

```
result = prdiffer__approve_pr(
  pr_url="https://github.com/owner/repo/pull/42",
  compliment="Great work on the refactoring!"
)
```

---

### prdiffer__describe_pr

Update a GitHub PR's description/body text.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_url` | `string` | Yes | Full GitHub PR URL |
| `pr_description` | `string` | Yes | New description text for the PR body |
| `api_key` | `string` | No | API key for authentication |

**Returns:** `string` - Success confirmation message.

**Example:**

```
result = prdiffer__describe_pr(
  pr_url="https://github.com/owner/repo/pull/42",
  pr_description="## Summary\nThis PR adds OAuth2 support..."
)
```

---

## Common Workflows

### Workflow 1: Analyze PR Changes

1. Extract the PR URL from user input or construct it from owner/repo/number.
2. Call `prdiffer__get_pr_diff(pr_url)`.
3. Iterate `result.files` to examine each changed file.
4. Use `file.status` to identify added, deleted, modified, or renamed files.
5. Use `file.stats.additions` and `file.stats.deletions` to quantify changes.
6. Use `file.diff` for the full patch content — parse hunks for line-by-line analysis.

### Workflow 2: Review and Approve

1. Fetch the diff via `prdiffer__get_pr_diff(pr_url)`.
2. Analyze the changes: check file statuses, review diff content, verify no suspicious patterns.
3. If the PR meets review criteria, call `prdiffer__approve_pr(pr_url, compliment)` with a meaningful compliment.

### Workflow 3: Summarize and Describe

1. Fetch the diff via `prdiffer__get_pr_diff(pr_url)`.
2. Generate a summary from the file list, change statistics, and diff content.
3. Call `prdiffer__describe_pr(pr_url, pr_description)` to update the PR body with the generated summary.

### Workflow 4: Extract File-Level Statistics

1. Call `prdiffer__get_pr_diff(pr_url)`.
2. Aggregate across `result.files`:
   - Total files changed: `len(result.files)`
   - Total additions: `sum(f.stats.additions for f in result.files)`
   - Total deletions: `sum(f.stats.deletions for f in result.files)`
   - Files by status: group by `f.status`

---

## Error Handling

All tools may raise exceptions. Catch and handle by error code:

```
try:
  result = prdiffer__get_pr_diff(pr_url)
except Exception as e:
  error_code = getattr(e, 'error_code', 'E5002_GITHUB_API_ERROR')
  match error_code:
    case "E1001_INVALID_URL":
      // Reconstruct URL from components and retry
    case "E2002_AUTH_FAILED":
      // Request api_key from user or check configuration
    case "E3001_RATE_LIMITED":
      // Wait (exponential backoff) and retry
    case "E5002_GITHUB_API_ERROR":
      // Verify repository access, check PR exists
    case _:
      // Log and report to user
```

---

## Constraints

- **PR URL format**: Must be a full GitHub URL: `https://github.com/{owner}/{repo}/pull/{number}`.
- **Authentication**: If the server has `MCP_AUTH_ENABLED=true`, every tool call requires a valid `api_key`.
- **Rate limiting**: The server enforces request limits. Avoid tight loops calling `get_pr_diff` repeatedly.
- **Caching**: The server uses commit-based cache invalidation. Repeated calls for the same PR return cached data until the PR is updated.
- **File filtering**: The server may apply pattern-based file filtering (configured server-side). Missing files in the response may be due to server-side filters.