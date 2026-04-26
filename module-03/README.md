# Module 3: The Full Stack Agent

**LLM + MCP + Tool Calling**

---

## What You'll Learn

- Connect to an MCP server using Streamable HTTP transport
- Discover and list available tools from the MCP server
- Integrate LLM inference with MCP tool calling
- Build an agentic chat loop that can use external tools

---

## Architecture

```
+--------+     +---------+     +------------+     +-------------+
|  User  | --> |   LLM   | --> | Tool Call? | --> | MCP Server  |
+--------+     +---------+     +------------+     +-------------+
    ^                               |                    |
    |                               v                    v
    +<-------- Final Response <---- + <-- Tool Result <--+
```

---

## Prerequisites

- Python 3.10+
- Completed Module 1 (LLM basics) and Module 2 (MCP Server)
- MCP server running and accessible
- API credentials (provided during workshop)

---

## Quick Start

### 1. Navigate to the module directory

```bash
cd module-03
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Create a `.env` file with your credentials:

```env
OPENAI_BASE_URL=<your-api-endpoint>
OPENAI_API_KEY=<your-api-key>
MCP_SERVER_URL=<your-mcp-server-url>
MCP_AUTH_TOKEN=<your-mcp-auth-token>
```

### 5. Run the notebook

Open `chat-app.ipynb` and follow the step-by-step instructions.

---

## Files in This Module

| File | Description |
|------|-------------|
| `chat-app.ipynb` | Step-by-step notebook with the full agent implementation |
| `requirements.txt` | Python dependencies |
| `.env` | Your API and MCP credentials (create this) |

---

## Key Concepts

### MCP Client Connection

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Create connection
streams_context = streamablehttp_client(
    url=server_url,
    headers={"Authorization": f"Bearer {token}"},
    timeout=60.0
)
read_stream, write_stream, _ = await streams_context.__aenter__()

# Create session
session = ClientSession(read_stream, write_stream)
await session.initialize()
```

### Tool Discovery

```python
# List available tools
response = await session.list_tools()
for tool in response.tools:
    print(f"{tool.name}: {tool.description}")
```

### Tool Execution

```python
# Call a tool
result = await session.call_tool(tool_name, tool_arguments)
```

### The Agentic Loop

1. Send user query + available tools to LLM
2. If LLM returns tool calls → execute via MCP
3. Send tool results back to LLM
4. Return final response to user

---

## Next Module

Once you've completed this module, move on to:

**Module 4: Code Whisperer** - Build a generic AI agent with MCP tools

```bash
cd ../module-4/code-review-agent
```
