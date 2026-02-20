# GitHub PR Review Tool - HTTP Server

A Flask-based HTTP server that provides RESTful endpoints for GitHub's PR review workflow. This server acts as a proxy to GitHub's API, making it easy to build PR review tools and integrations.

## Features

### Read Operations
- **Pull Requests**: List PRs, get PR details, view files changed, list PR commits
- **Commits**: List commits, get commit details
- **Comments**: List PR comments
- **Reviews**: List reviews, get review details
- **Review Comments**: List code review comments
- **Files**: Get file contents at any ref
- **Branches**: List and get branch info
- **Compare**: Compare commits/branches

### Write Operations (requires `GITHUB_TOKEN`)
- **Comments**: Create, update PR comments
- **Reviews**: Create reviews (Approve, Request Changes, Comment)
- **Review Comments**: Create, update, and reply to code review comments

## Quick Start

### 1. Clone and Setup

```bash
cd /path/to/AgentOps

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure GitHub Token

Create a `.env` file or export the environment variable:

```bash
export GITHUB_TOKEN="your_github_personal_access_token"
```

**Required token scopes:**
- `repo` - Full control of private repositories
- `public_repo` - Access public repositories (for public repos only)

[Create a GitHub Personal Access Token](https://github.com/settings/tokens/new)

### 3. Run the Server

```bash
python app.py
```

The server will start at `http://localhost:5000`

### Optional Environment Variables

```bash
export PORT=5000           # Server port (default: 5000)
export DEBUG=true          # Enable debug mode (default: false)
```

## API Reference

### Base URL
```
http://localhost:5000
```

### Authentication
- Set the `GITHUB_TOKEN` environment variable
- Write operations (POST, PATCH, DELETE, PUT) require authentication
- Read operations work without a token but have lower rate limits

---

### Pull Requests

#### List Pull Requests
```http
GET /repos/{owner}/{repo}/pulls
```

Query Parameters:
| Parameter | Default | Description |
|-----------|---------|-------------|
| state | open | `open`, `closed`, `all` |
| sort | created | `created`, `updated`, `popularity` |
| direction | desc | `asc`, `desc` |
| per_page | 30 | Results per page (max: 100) |
| page | 1 | Page number |

#### Get Pull Request
```http
GET /repos/{owner}/{repo}/pulls/{pull_number}
```

#### Get PR Files (Diff)
```http
GET /repos/{owner}/{repo}/pulls/{pull_number}/files
```

#### Get PR Commits
```http
GET /repos/{owner}/{repo}/pulls/{pull_number}/commits
```

---

### Commits

#### List Commits
```http
GET /repos/{owner}/{repo}/commits
```

Query Parameters:
| Parameter | Description |
|-----------|-------------|
| sha | Branch or SHA to start from |
| path | Filter by file path |
| author | Filter by author |
| since | ISO 8601 date |
| until | ISO 8601 date |

#### Get Commit
```http
GET /repos/{owner}/{repo}/commits/{ref}
```

---

### Comments (PR Conversation)

#### List Comments
```http
GET /repos/{owner}/{repo}/issues/{issue_number}/comments
```

#### Create Comment
```http
POST /repos/{owner}/{repo}/issues/{issue_number}/comments

{
  "body": "Great work on this PR!"
}
```

#### Update Comment
```http
PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}

{
  "body": "Updated comment text"
}
```

---

### Reviews (Approve/Request Changes)

#### List Reviews
```http
GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews
```

#### Create Review
```http
POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews

{
  "event": "APPROVE",  // or "REQUEST_CHANGES" or "COMMENT"
  "body": "Looks good to me!"
}
```

With review comments:
```http
POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews

{
  "event": "REQUEST_CHANGES",
  "body": "Please address the following issues:",
  "comments": [
    {
      "path": "src/utils.js",
      "line": 42,
      "body": "This function needs error handling"
    }
  ]
}
```

#### Dismiss Review
```http
PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismiss

{
  "message": "Dismissing due to updated changes"
}
```

---

### Review Comments (Code-Level Comments)

These are comments on specific lines of code in the diff.

#### List Review Comments
```http
GET /repos/{owner}/{repo}/pulls/{pull_number}/comments
```

#### Create Review Comment
```http
POST /repos/{owner}/{repo}/pulls/{pull_number}/comments

{
  "body": "Consider using a constant here",
  "commit_id": "abc123def456",
  "path": "src/config.js",
  "line": 15,
  "side": "RIGHT"
}
```

Multi-line comment:
```http
{
  "body": "This entire block could be simplified",
  "commit_id": "abc123def456",
  "path": "src/utils.js",
  "start_line": 10,
  "line": 25,
  "start_side": "RIGHT",
  "side": "RIGHT"
}
```

#### Reply to Review Comment
```http
POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/replies

{
  "body": "Good point, I'll fix this"
}
```

---

### Compare

#### Compare Branches/Commits
```http
GET /repos/{owner}/{repo}/compare/{base}...{head}
```

Example:
```http
GET /repos/octocat/hello-world/compare/main...feature-branch
```

---

### File Contents

#### Get File Contents
```http
GET /repos/{owner}/{repo}/contents/{path}?ref={branch}
```

---

## Example Usage with curl

### List Open PRs
```bash
curl http://localhost:5000/repos/facebook/react/pulls
```

### Get PR Details
```bash
curl http://localhost:5000/repos/facebook/react/pulls/12345
```

### View PR Diff
```bash
curl http://localhost:5000/repos/facebook/react/pulls/12345/files
```

### Add a Comment
```bash
curl -X POST http://localhost:5000/repos/owner/repo/issues/123/comments \
  -H "Content-Type: application/json" \
  -d '{"body": "LGTM! 🎉"}'
```

### Approve a PR
```bash
curl -X POST http://localhost:5000/repos/owner/repo/pulls/123/reviews \
  -H "Content-Type: application/json" \
  -d '{"event": "APPROVE", "body": "Ship it!"}'
```

### Request Changes
```bash
curl -X POST http://localhost:5000/repos/owner/repo/pulls/123/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "event": "REQUEST_CHANGES",
    "body": "Please address these issues",
    "comments": [
      {
        "path": "src/index.js",
        "line": 42,
        "body": "Missing null check"
      }
    ]
  }'
```

## Rate Limiting

GitHub API has rate limits:
- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5,000 requests/hour

The server passes through GitHub's rate limit headers in responses.

## Error Handling

All endpoints return JSON with appropriate HTTP status codes:

```json
{
  "error": "Error description",
  "message": "Additional details"
}
```

Common status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (missing required fields)
- `401` - Unauthorized (token required)
- `404` - Not Found
- `422` - Unprocessable Entity (validation error)
- `403` - Forbidden (rate limited or insufficient permissions)

## Project Structure

```
AgentOps/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## License

MIT
