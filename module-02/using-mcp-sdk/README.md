# Module 2: Building & Registering MCP Servers

Build a local MCP server using the **Python MCP SDK** that wraps the GitHub REST API into three tools an AI assistant can use.

## What You'll Learn

- Create an MCP server with `FastMCP`
- Register tools using `@mcp.tool()` — the SDK auto-generates JSON Schemas from type hints and docstrings
- Understand how `list_tools` and `call_tool` handlers work
- Run the server via stdio and connect it to Cursor

## Tools

| Tool | Description | Auth required? |
|------|-------------|---------------|
| `get_repos` | List repositories for a GitHub user/org | No (public repos) |
| `get_pull_requests` | List pull requests for a repository | No (public repos) |
| `write_pull_request_review` | Post a review comment on a PR | Yes (`GITHUB_TOKEN`) |

## Setup

```bash
cd module-02/using-mcp-sdk
pip install -r requirements.txt
```

Create a `module-02/.env` file (or export the variable):

```
GITHUB_TOKEN=ghp_your_token_here
```

A token is only required for `write_pull_request_review`. The read-only tools work without one on public repos.

## Workshop Flow

1. **Open `mcp_server.ipynb`** and walk through each cell:
   - Step 1–2: Install deps & create the `FastMCP` server
   - Step 3: Define the three tools with `@mcp.tool()`
   - Step 4: Inspect `list_tools` to see auto-generated schemas
   - Step 5: Test each tool by calling it directly
   - Step 6–7: Run `server.py` and connect to Cursor

2. **Run the server locally:**

   ```bash
   python server.py
   ```

3. **Register in Cursor** — add to `.cursor/mcp.json`:

   ```json
   {
     "mcpServers": {
       "github-tools": {
         "command": "python3",
         "args": ["/absolute/path/to/module-02/using-mcp-sdk/server.py"],
         "env": { "GITHUB_TOKEN": "your_token" }
       }
     }
   }
   ```

## Project Structure

```
module-02/
├── .env                 # GITHUB_TOKEN (not committed)
├── .env.example.json    # Example env vars
└── using-mcp-sdk/
    ├── server.py            # Runnable MCP server (stdio transport)
    ├── mcp_server.ipynb     # Workshop notebook — step-by-step walkthrough
    ├── requirements.txt
    └── README.md            # You are here
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub PAT — required for write operations | — |
