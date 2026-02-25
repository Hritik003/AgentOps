# MCP Proxy – HTTP server that exposes code-review-server as MCP tools

A **pure Python** HTTP server that speaks the [Model Context Protocol](https://modelcontextprotocol.io) (MCP) over JSON-RPC and proxies every tool call to the [code-review-server](../code-review-server/) HTTP API. **No MCP SDK** is used; the proxy is implemented from the ground up so that every API call flows through the MCP workflow.

## Architecture

```
MCP client (e.g. Cursor, Claude Desktop)
    → HTTP POST (JSON-RPC: initialize, tools/list, tools/call)
        → mcp-proxy (this server)
            → HTTP GET/POST/PATCH/PUT to code-review-server
                → code-review-server → GitHub API
```

- **code-review-server**: Flask app that exposes GitHub PR/review operations as REST endpoints.
- **mcp-proxy**: HTTP server that implements MCP (initialize, tools/list, tools/call) and, for each tool call, performs the corresponding HTTP request to code-review-server and returns the result as MCP text content.

## Requirements

- Python 3.10+
- **No third-party dependencies** – uses only the standard library (`json`, `http.server`, `urllib`, `ssl`).

## Setup

1. **Start the code-review-server** (so the proxy has a backend to call):

   ```bash
   cd code-review-server
   pip install -r requirements.txt
   export GITHUB_TOKEN=your_token   # optional but required for write operations
   python app.py
   ```

   By default it runs at `http://localhost:5000`.

2. **Start the MCP proxy**:

   ```bash
   cd mcp-proxy
   python server.py
   ```

   By default the proxy listens on `http://0.0.0.0:8080`.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODE_REVIEW_SERVER_URL` | `http://localhost:5000` | Base URL of the code-review-server. |
| `MCP_PROXY_PORT` | `8080` | Port the proxy HTTP server binds to. |

Example:

```bash
export CODE_REVIEW_SERVER_URL=http://localhost:5000
export MCP_PROXY_PORT=8080
python server.py
```

## MCP endpoint

- **URL**: `http://localhost:8080/` or `http://localhost:8080/mcp`
- **Method**: `POST`
- **Body**: JSON-RPC 2.0 request
- **Response**: JSON-RPC 2.0 response

Supported methods:

- `initialize` – Returns server info and capabilities (including `tools`).
- `initialized` – Notification; no response body.
- `tools/list` – Returns the list of tools (same logical set as code-review-mcp-server).
- `tools/call` – Executes a tool by calling the code-review-server HTTP API and returns `content` with type `text`.

## Tools exposed

The proxy exposes the same logical tools as the code-review-mcp-server, each implemented by one or more HTTP calls to code-review-server:

| Tool | Backend API |
|------|-------------|
| `get_repository` | GET /repos/{owner}/{repo} |
| `list_pull_requests` | GET /repos/{owner}/{repo}/pulls |
| `get_pull_request` | GET /repos/{owner}/{repo}/pulls/{pull_number} |
| `get_pull_request_files` | GET .../pulls/{pull_number}/files |
| `get_pull_request_commits` | GET .../pulls/{pull_number}/commits |
| `list_commits` | GET /repos/{owner}/{repo}/commits |
| `get_commit` | GET /repos/{owner}/{repo}/commits/{ref} |
| `list_reviews` | GET .../pulls/{pull_number}/reviews |
| `get_review` | GET .../pulls/{pull_number}/reviews/{review_id} |
| `create_review` | POST .../pulls/{pull_number}/reviews |
| `update_review` | PUT .../pulls/.../reviews/{review_id} |
| `dismiss_review` | PUT .../pulls/.../reviews/{review_id}/dismiss |
| `list_review_comments` | GET .../pulls/{pull_number}/comments |
| `create_review_comment` | POST .../pulls/{pull_number}/comments |
| `update_review_comment` | PATCH .../pulls/comments/{comment_id} |
| `reply_to_review_comment` | POST .../pulls/comments/{comment_id}/replies |
| `list_issue_comments` | GET .../issues/{issue_number}/comments |
| `create_issue_comment` | POST .../issues/{issue_number}/comments |
| `update_issue_comment` | PATCH .../issues/comments/{comment_id} |
| `get_file_contents` | GET .../contents/{path} |
| `list_branches` | GET .../branches |
| `get_branch` | GET .../branches/{branch} |
| `compare_commits` | GET .../compare/{base}...{head} |

## Example: calling the proxy with curl

### 1. Initialize

```bash
curl -s -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### 2. List tools

```bash
curl -s -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

### 3. Call a tool

```bash
curl -s -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_repository","arguments":{"owner":"octocat","repo":"hello-world"}}}'
```

## Project structure

```
mcp-proxy/
├── server.py        # HTTP server + MCP JSON-RPC handlers (no SDK)
├── tools.py         # Tool definitions (name, description, inputSchema)
├── proxy.py         # Maps tool name + args → HTTP request to code-review-server
├── requirements.txt # No dependencies (stdlib only)
└── README.md
```

## Connecting an MCP client

MCP clients that support **HTTP** transport can point to:

- `http://localhost:8080/` or `http://localhost:8080/mcp`

and send JSON-RPC requests as above. If your client expects **stdio** transport (e.g. some Cursor/Claude configs), you would need a small adapter that reads JSON-RPC from stdin and forwards it over HTTP to this server and writes the response to stdout; this repo does not include that adapter.

## Reference

- [Build an MCP server (modelcontextprotocol.io)](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP Tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
