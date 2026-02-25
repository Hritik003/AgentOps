"""
Minimal Code Review Agent

Uses 2 MCP tools from code-review-mcp-server:
  1. get_pull_request_files - fetch PR diff for review
  2. create_issue_comment   - post review as a PR comment

Runs an agentic loop with an OpenAI-compliant inference endpoint.
"""

import json
import os
import sys

import requests
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MCP_URL = os.environ.get("MCP_PROXY_URL", "http://localhost:8080").rstrip("/")
MCP_BEARER_TOKEN = os.environ.get("MCP_PROXY_BEARER_TOKEN", "").strip()  # Optional Bearer auth for MCP proxy
OPENAI_BASE = os.environ.get("OPENAI_API_BASE")  # Your OpenAI-compliant endpoint base URL
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "dummy")  # API key for the endpoint

# Only these 2 tools are exposed to the model
TOOL_NAMES = ["get_pull_request_files", "create_issue_comment"]

# ---------------------------------------------------------------------------
# MCP client (HTTP JSON-RPC)
# ---------------------------------------------------------------------------

def _mcp_headers() -> dict:
    """Build headers for MCP proxy requests, including optional Bearer auth."""
    headers = {"Content-Type": "application/json"}
    if MCP_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {MCP_BEARER_TOKEN}"
    return headers


def mcp_request(method: str, params: dict | None = None) -> dict:
    """Send a single JSON-RPC request to the MCP server."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    resp = requests.post(
        f"{MCP_URL}/",
        json=payload,
        headers=_mcp_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", data["error"]))
    return data.get("result", {})


def mcp_initialize():
    """Initialize MCP session."""
    return mcp_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "code-review-agent", "version": "1.0"},
    })


def mcp_list_tools() -> list[dict]:
    """Fetch all tools from MCP and return only the 2 we need."""
    result = mcp_request("tools/list")
    all_tools = result.get("tools", [])
    return [t for t in all_tools if t.get("name") in TOOL_NAMES]


def mcp_call_tool(name: str, arguments: dict) -> str:
    """Execute one tool and return the text result."""
    result = mcp_request("tools/call", {"name": name, "arguments": arguments})
    content = result.get("content", [])
    if not content:
        return ""
    for part in content:
        if part.get("type") == "text":
            return part.get("text", "")
    return ""


# ---------------------------------------------------------------------------
# Convert MCP tool schema to OpenAI function format
# ---------------------------------------------------------------------------

def mcp_tools_to_openai(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool definitions to OpenAI chat completions tools format."""
    openai_tools = []
    for t in mcp_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        })
    return openai_tools


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a code review agent. You have access to two tools:

1. get_pull_request_files(owner, repo, pull_number) - Get the list of files changed in a pull request with their diffs and change statistics. Use this first to see what code changed.

2. create_issue_comment(owner, repo, issue_number, body) - Create a comment on the pull request. Use this to post your review. For a PR, issue_number is the same as the pull request number.

Your task: Review the code for the given PR and then post a single, concise review comment summarizing your findings (what looks good, any suggestions or concerns). Use the tools in order: first get the PR files, then write the review comment. After posting the comment, reply with a short confirmation to the user."""


def run_agent(owner: str, repo: str, pull_number: int) -> str:
    """
    Run the code review agent: fetch PR files via MCP, let the model produce a review,
    then post it as a PR comment via MCP. Returns the final assistant message to the user.
    """
    if not OPENAI_BASE:
        raise ValueError("Set OPENAI_API_BASE to your OpenAI-compliant inference endpoint URL")

    client = OpenAI(
        base_url=OPENAI_BASE,
        api_key=OPENAI_KEY,
    )

    mcp_initialize()
    mcp_tool_list = mcp_list_tools()
    
    openai_tools = mcp_tools_to_openai(mcp_tool_list)
    user_message = (
        f"Please review the code for this pull request and add a comment with your review.\n"
        f"Repository: {owner}/{repo}\n"
        f"Pull request number: {pull_number}\n"
        f"Use get_pull_request_files first, then create_issue_comment to post your review."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    max_turns = 10
    final_content = ""

    for _ in range(max_turns):
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message
        finish = choice.finish_reason

        if msg.content:
            final_content = (msg.content or "").strip()

        if finish == "stop" and not getattr(msg, "tool_calls", None):
            return final_content or "Review flow finished."

        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            return final_content or "Review flow finished."

        # Append assistant message with tool calls
        assistant_msg = {
            "role": "assistant",
            "content": msg.content or None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)

        # Execute each tool and append tool results
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
            except json.JSONDecodeError:
                args = {}
            try:
                result = mcp_call_tool(name, args)
            except Exception as e:
                result = json.dumps({"error": str(e)})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return final_content or "Max turns reached."


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        print("Usage: python agent.py <owner> <repo> <pull_number>", file=sys.stderr)
        print("Example: python agent.py octocat hello-world 123", file=sys.stderr)
        sys.exit(1)
    owner, repo, pull_number = sys.argv[1], sys.argv[2], int(sys.argv[3])
    try:
        out = run_agent(owner, repo, pull_number)
        print(out)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
