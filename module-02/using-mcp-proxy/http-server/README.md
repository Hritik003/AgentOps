# GitHub PR Review Tool – HTTP Server

Minimal Flask server for a **code review agent**. It exposes two APIs that proxy to the GitHub API:

1. **Get pull request files** – changed files and diffs for a given PR  
2. **Add PR review comment** – submit a review on the PR (comment, approve, or request changes)

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check; reports token configured or not |
| `/repos/{owner}/{repo}/pulls/{pull_number}/files` | GET | Get PR changed files and diffs (optional: `per_page`, `page`) |
| `/repos/{owner}/{repo}/pulls/{pull_number}/reviews` | POST | Create a PR review. Body: `{"event": "COMMENT"\|"APPROVE"\|"REQUEST_CHANGES", "body": "..."}` |

- **Get files** works without a token (subject to GitHub rate limits for unauthenticated requests).  
- **Create review** requires `GITHUB_TOKEN`; returns 401 if the token is not set.

## Quick start

```bash
pip install -r requirements.txt
export GITHUB_TOKEN=your_token   # required for create_pr_review
python app.py
```

Server runs at `http://localhost:5000` by default.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | — | GitHub PAT; required for POST .../reviews |
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Set to `true` to run Flask in debug mode |

## Examples

**Get PR files (no auth needed for public repos):**

```bash
curl "http://localhost:5000/repos/octocat/hello-world/pulls/1/files"
```

**Add a review comment:**

```bash
curl -X POST http://localhost:5000/repos/OWNER/REPO/pulls/PR_NUMBER/reviews \
  -H "Content-Type: application/json" \
  -d '{"event": "COMMENT", "body": "LGTM!"}'
```

**Approve a PR:**

```bash
curl -X POST http://localhost:5000/repos/OWNER/REPO/pulls/PR_NUMBER/reviews \
  -H "Content-Type: application/json" \
  -d '{"event": "APPROVE", "body": "Looks good to me."}'
```

## Project structure

```
http-server/
├── app.py              # Flask app and routes
├── requirements.txt
├── tutorial.ipynb      # Step-by-step notebook
└── README.md
```

## See also

- **mcp-proxy** (`../mcp-proxy/`) – MCP server that exposes these two operations as tools for AI agents.  
- **tutorial.ipynb** – Notebook that builds the same two endpoints step by step.
