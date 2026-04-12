# MCP Proxy (code review agent)

**Streamable HTTP** MCP server: one endpoint for POST (JSON-RPC) and GET (SSE). Proxies **2 tools** to the [http-server](../http-server/) backend:

| Tool | Description |
|------|-------------|
| `get_pull_request_files` | Get files changed in a PR (diffs and stats) |
| `create_pr_review` | Add a PR review comment (COMMENT, APPROVE, REQUEST_CHANGES) |

## Architecture

```
MCP client (e.g. code review agent)
    → POST/GET to MCP endpoint (Streamable HTTP)
        → mcp-proxy (this server)
            → HTTP to http-server
                → GitHub API
```

## Setup

1. Start the http-server (backend):

   ```bash
   cd ../http-server
   pip install -r requirements.txt
   export GITHUB_TOKEN=your_token
   python app.py
   ```
   Default: `http://localhost:5000`

2. Start the MCP proxy:

   ```bash
   cd mcp-proxy
   python server.py
   ```
   Default: `http://0.0.0.0:8080`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODE_REVIEW_SERVER_URL` | `http://localhost:5000` | Backend http-server URL |
| `MCP_PROXY_PORT` | `8080` | Proxy port |

## MCP endpoint (Streamable HTTP)

- **URL**: `http://localhost:8080/mcp` (or `http://localhost:8080/`)
- **POST**: JSON-RPC 2.0 body. Requests get `200` + JSON; notifications get `202 Accepted`.
- **GET**: Opens an SSE stream (`Content-Type: text/event-stream`); minimal stream (one event then close).
- **Methods**: `initialize`, `tools/list`, `tools/call`; `initialized` as notification → 202.

## Example: list tools

```bash
curl -s -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Test with MCP client SDK

A shared client in **module-02/mcp-client/** uses the official [MCP Python SDK](https://pypi.org/project/mcp/) (Streamable HTTP) and works with both this proxy and the using-mcp-sdk server:

```bash
cd ../../mcp-client
pip install -r requirements.txt
python client_demo.py http://localhost:8080/mcp
```

Use `MCP_PROXY_URL` or pass the endpoint URL as the first argument.

## Project structure

```
mcp-proxy/
├── server.py
├── tools.py      # 2 tool definitions
├── proxy.py      # Maps tools → http-server API
└── README.md
```
