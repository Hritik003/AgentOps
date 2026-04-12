# GitHub PR Review Tool - MCP Server (minimal)

MCP server that exposes **only 2 tools** for a code review agent:

| Tool | Description |
|------|-------------|
| `get_pull_request_files` | Get files changed in a PR with diffs and stats |
| `create_issue_comment` | Create a comment on a PR (e.g. post the review) |

## Setup

```bash
cd module-02/using-mcp-sdk
pip install -r requirements.txt
export GITHUB_TOKEN=your_token   # required for create_issue_comment
```

## Running the server

### Stdio (local / Cursor)

```bash
python server_stdio.py
```

Cursor config example:

```json
{
  "mcpServers": {
    "github-pr-review": {
      "command": "python3",
      "args": ["/path/to/module-02/using-mcp-sdk/server_stdio.py"],
      "env": { "GITHUB_TOKEN": "your_github_token_here" }
    }
  }
}
```

### HTTP (Docker / production)

```bash
python server_http.py
```

- MCP: `http://localhost:8000/mcp`
- Health: `http://localhost:8000/health`

**Test with MCP client:** Use the client in **module-02/mcp-client/** to test  this server:

```bash
cd ../mcp-client
pip install -r requirements.txt
python client_demo.py http://localhost:8000/mcp
```

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub PAT (required for create_issue_comment) | - |
| `MCP_HOST` | Bind address (HTTP mode) | `0.0.0.0` |
| `MCP_PORT` | Port (HTTP mode) | `8000` |

## Project structure

```
using-mcp-sdk/
├── server_stdio.py   # stdio transport
├── server_http.py   # streamable HTTP transport
├── requirements.txt
├── Dockerfile
├── tutorial.ipynb
└── README.md
```
