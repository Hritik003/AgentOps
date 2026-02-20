# GitHub PR Review Tool - MCP Server

An MCP (Model Context Protocol) server that provides GitHub API tools for AI-assisted PR review workflows. This server allows AI assistants like Claude to interact with GitHub repositories, pull requests, reviews, and comments.

## What is MCP?

MCP (Model Context Protocol) is a standardized protocol that allows AI assistants to interact with external tools and data sources. Instead of making HTTP requests, the AI directly calls "tools" exposed by your server.

## Features

### Read Tools
- **Pull Requests**: List PRs, get PR details, view files changed, list PR commits
- **Commits**: List commits, get commit details
- **Reviews**: List reviews, get review details
- **Review Comments**: List code review comments
- **Files**: Get file contents at any branch/commit
- **Branches**: List and get branch info
- **Compare**: Compare branches/commits

### Write Tools (requires `GITHUB_TOKEN`)
- **Reviews**: Create reviews (Approve, Request Changes, Comment)
- **Review Comments**: Create, update, and reply to code review comments

## Installation

### 1. Clone and Setup

```bash
cd /path/to/code-review-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure GitHub Token

```bash
export GITHUB_TOKEN="your_github_personal_access_token"
```

**Required token scopes:**
- `repo` - Full control of private repositories
- `public_repo` - Access public repositories only

[Create a GitHub Personal Access Token](https://github.com/settings/tokens/new)

### 3. Test the Server

```bash
python server.py
```

The server communicates via stdio (standard input/output), so you won't see any output unless there's an error.

## Configure with Claude Desktop

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github-pr-review": {
      "command": "python",
      "args": ["/absolute/path/to/code-review-mcp-server/server.py"],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

Or with a virtual environment:

```json
{
  "mcpServers": {
    "github-pr-review": {
      "command": "/absolute/path/to/code-review-mcp-server/venv/bin/python",
      "args": ["/absolute/path/to/code-review-mcp-server/server.py"],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

## Configure with Cursor

Add to your Cursor MCP settings (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "github-pr-review": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/absolute/path/to/code-review-mcp-server",
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

## Available Tools

### Pull Requests

| Tool | Description |
|------|-------------|
| `list_pull_requests` | List PRs for a repository |
| `get_pull_request` | Get details of a specific PR |
| `get_pull_request_files` | Get files changed in a PR |
| `get_pull_request_commits` | List commits in a PR |

### Commits

| Tool | Description |
|------|-------------|
| `list_commits` | List commits in a repository |
| `get_commit` | Get details of a specific commit |

### Reviews

| Tool | Description |
|------|-------------|
| `list_reviews` | List reviews on a PR |
| `get_review` | Get a specific review |
| `create_review` | Create a review (APPROVE/REQUEST_CHANGES/COMMENT) |
| `update_review` | Update review body |
| `dismiss_review` | Dismiss a review |

### Review Comments

| Tool | Description |
|------|-------------|
| `list_review_comments` | List inline code comments |
| `create_review_comment` | Comment on specific code line |
| `update_review_comment` | Update a comment |
| `reply_to_review_comment` | Reply to a comment thread |

### Repository

| Tool | Description |
|------|-------------|
| `get_repository` | Get repository information |
| `get_file_contents` | Get file contents |
| `list_branches` | List branches |
| `get_branch` | Get branch details |
| `compare_commits` | Compare branches/commits |

## Example Conversations

Once configured, you can ask Claude things like:

- "List the open pull requests in facebook/react"
- "Show me the files changed in PR #1234 of my-org/my-repo"
- "What are the reviews on PR #567?"
- "Approve PR #890 in owner/repo with message 'LGTM!'"
- "Compare main and develop branches in my-org/my-repo"
- "Add a review comment on line 42 of src/index.js saying 'Consider adding error handling'"

## Project Structure

```
code-review-mcp-server/
├── server.py           # MCP server with all tool definitions
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Troubleshooting

### "GitHub token not configured"
Make sure `GITHUB_TOKEN` is set in your environment or MCP configuration.

### Server not appearing in Claude
1. Check the path in your config is absolute
2. Restart Claude Desktop after config changes
3. Check Claude's logs for errors

### Rate limiting
- Unauthenticated: 60 requests/hour
- Authenticated: 5,000 requests/hour

## License

MIT

