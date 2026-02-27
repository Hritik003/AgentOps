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
MCP_URL = os.environ.get("MCP_PROXY_URL", "http://localhost:8000/mcp").rstrip("/")
MCP_BEARER_TOKEN = os.environ.get("MCP_PROXY_BEARER_TOKEN", "").strip()  # Optional Bearer auth for MCP proxy
OPENAI_BASE = os.environ.get("OPENAI_API_BASE")  # Your OpenAI-compliant endpoint base URL
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "dummy")  # API key for the endpoint
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "oss-demo-1")

# ---------------------------------------------------------------------------
# MCP client (HTTP JSON-RPC)
# ---------------------------------------------------------------------------

# Session ID from server; capture from initialize (and any) response, send on all subsequent requests.
MCP_SESSION_ID: list[str | None] = [None]


def _mcp_headers() -> dict:
    """Build headers for MCP proxy requests: Accept for JSON/SSE, optional Bearer auth, session ID."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if MCP_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {MCP_BEARER_TOKEN}"
    if MCP_SESSION_ID[0]:
        headers["Mcp-Session-Id"] = MCP_SESSION_ID[0]
    return headers


def _parse_mcp_response_body(text: str) -> dict:
    """Parse MCP response: plain JSON or SSE (event: message, data: {...})."""
    if not text or not text.strip():
        return {}
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    if "data:" in text:
        data_parts = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data_parts.append(line[5:].strip())
        if data_parts:
            json_str = "\n".join(data_parts)
            if json_str:
                return json.loads(json_str)
    return json.loads(text)


def _capture_session_id(resp: requests.Response) -> None:
    """Extract MCP session ID from response headers or body and store for subsequent requests."""
    sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
    if not sid and (resp.text or "").strip():
        try:
            data = _parse_mcp_response_body(resp.text)
            result = data.get("result") if isinstance(data, dict) else data
            if isinstance(result, dict):
                sid = result.get("sessionId") or result.get("session_id")
        except Exception:
            pass
    if sid:
        MCP_SESSION_ID[0] = sid


def mcp_request(method: str, params: dict | None = None) -> dict:
    """Send a single JSON-RPC request to the MCP server."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    try:
        resp = requests.post(MCP_URL, json=payload, headers=_mcp_headers(), timeout=60)
    except (requests.exceptions.ConnectTimeout, requests.exceptions.Timeout) as e:
        raise RuntimeError(
            f"MCP connection to {MCP_URL} timed out. "
            "Check network access, VPN, or firewall. If using a remote MCP, ensure the host is reachable."
        ) from e
    _capture_session_id(resp)
    resp.raise_for_status()
    if not (resp.text or "").strip():
        data = {}
    else:
        try:
            data = _parse_mcp_response_body(resp.text)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"MCP response is not JSON. Status: {resp.status_code}. Body: {(resp.text or '')[:300]!r}"
            )
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
    return all_tools


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

SYSTEM_PROMPT = """You are a code review agent. You can get pull request files. If you have the pull request files, you can create a review comment on a pull request.
Your task: Review the code for the given PR and then post a single, concise review comment summarizing your findings (what looks good, any suggestions or concerns). Use the tools available to you in order. First get the PR files, go through them, then write the review comment. After posting the comment, reply with a short confirmation to the user."""


def run_agent(owner: str, repo: str, pull_number: int) -> str:
    """
    Run the code review agent: fetch PR files via MCP, let the model produce a review,
    then post it as a PR comment via MCP. Returns the final assistant message to the user.
    """
    if not OPENAI_BASE:
        raise ValueError("Set OPENAI_API_BASE to your OpenAI-compliant inference endpoint URL")

    # If OPENAI_BASE is a full chat/completions URL, strip that path so the client can append it.
    base_url = (
        OPENAI_BASE.rsplit("/chat/completions", 1)[0]
        if "/chat/completions" in OPENAI_BASE
        else OPENAI_BASE.rstrip("/")
    )
    client = OpenAI(base_url=base_url, api_key=OPENAI_KEY)

    mcp_initialize()
    mcp_tool_list = mcp_list_tools()
    
    openai_tools = mcp_tools_to_openai(mcp_tool_list)
    user_message = (
        f"Please review the code for this pull request and add a comment with your review.\n"
        f"Repository: {owner}/{repo}\n"
        f"Pull request number: {pull_number}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    max_turns = 10
    final_content = ""

    for _ in range(max_turns):
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
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
