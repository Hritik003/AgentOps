# MCP Client (Streamable HTTP)

MCP client for testing **Streamable HTTP** MCP servers in module-02. Uses the official [MCP Python SDK](https://pypi.org/project/mcp/).

Works with:

| Server | Path | Default URL |
|--------|------|-------------|
| **mcp-proxy** | `using-mcp-proxy/mcp-proxy/server.py` | `http://localhost:8080/mcp` |
| **using-mcp-sdk** | `using-mcp-sdk/server_http.py` | `http://localhost:8000/mcp` |

## Setup

```bash
cd module-02/mcp-client
pip install -r requirements.txt
```

## Run

```bash
# Default (proxy on 8080)
python client_demo.py

# SDK server (port 8000)
python client_demo.py http://localhost:8000/mcp

# Or set env
export MCP_SERVER_URL=http://localhost:8000/mcp
python client_demo.py
```

The client runs `initialize`, `tools/list`, and `tools/call` (get_pull_request_files).

## Tutorial

**tutorial.ipynb** walks through the same flow in Jupyter: connect, initialize, list tools, call `get_pull_request_files`, and call `create_pr_review`. Open it in Jupyter or VS Code and run the cells (ensure one of the servers is running and `MCP_SERVER_URL` or the URL in the notebook points to it).
