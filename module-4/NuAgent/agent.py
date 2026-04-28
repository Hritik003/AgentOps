"""
Generic AI Agent

Interactive CLI agent that can use any MCP tools (GitHub, Jira, etc.)
to accomplish tasks described in natural language.

Runs an agentic loop with an OpenAI-compliant inference endpoint.
"""

import json
import os
import re
import sys

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Config — loaded from .env
# ---------------------------------------------------------------------------
MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp").rstrip("/")
MCP_BEARER_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()
OPENAI_BASE = os.getenv("OPENAI_BASE_URL")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "dummy")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gptoss120b--ep-klmd")

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
    """Fetch all available tools from MCP."""
    result = mcp_request("tools/list")
    return result.get("tools", [])


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

SYSTEM_PROMPT = """You are a helpful AI agent with access to tools for interacting with GitHub repositories, Jira issues, and more.

When the user asks you to accomplish a task, break it down into steps and use the available tools to complete each step. You may need to call multiple tools in sequence — do so until the task is fully complete. After finishing, reply with a concise summary of what you did."""


def _agent_loop(client, messages, openai_tools, max_turns=15):
    """Inner loop: let the LLM call tools across multiple turns until done."""
    final_content = ""
    for turn in range(max_turns):
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message

        print(f"\n--- Turn {turn + 1} (finish_reason={choice.finish_reason}) ---")
        if msg.content:
            print(f"Assistant: {msg.content}")
            final_content = msg.content.strip()

        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            return final_content or "Done."

        for tc in tool_calls:
            print(f"  Tool call: {tc.function.name}({tc.function.arguments[:200]})")

        assistant_msg = {
            "role": "assistant",
            "content": msg.content or None,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in tool_calls:
            name = re.sub(r"<\|[^|]*\|>[^\s]*", "", tc.function.name).strip()
            tc.function.name = name
            try:
                args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
            except json.JSONDecodeError:
                args = {}
            try:
                result = mcp_call_tool(name, args)
            except Exception as e:
                result = json.dumps({"error": str(e)})
            print(f"  Result ({name}): {result[:300]}...")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return final_content or "Max turns reached."


def interactive_chat(max_turns_per_query: int = 15):
    """
    Interactive chat loop: continuously prompts for user input,
    runs the agent loop for each query, and keeps conversation history.
    Type 'exit' or 'quit' to stop.
    """
    if not OPENAI_BASE:
        raise ValueError("Set OPENAI_BASE_URL in your .env file")

    base_url = (
        OPENAI_BASE.rsplit("/chat/completions", 1)[0]
        if "/chat/completions" in OPENAI_BASE
        else OPENAI_BASE.rstrip("/")
    )
    client = OpenAI(base_url=base_url, api_key=OPENAI_KEY)

    mcp_initialize()
    mcp_tool_list = mcp_list_tools()
    openai_tools = mcp_tools_to_openai(mcp_tool_list)
    print(f"Loaded {len(mcp_tool_list)} MCP tools.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("\nInteractive Agent Chat (type 'exit' to quit)")
    print("=" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})
        result = _agent_loop(client, messages, openai_tools, max_turns=max_turns_per_query)
        messages.append({"role": "assistant", "content": result})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        if not OPENAI_BASE:
            raise ValueError("Set OPENAI_BASE_URL in your .env file")
        base_url = (
            OPENAI_BASE.rsplit("/chat/completions", 1)[0]
            if "/chat/completions" in OPENAI_BASE
            else OPENAI_BASE.rstrip("/")
        )
        client = OpenAI(base_url=base_url, api_key=OPENAI_KEY)
        mcp_initialize()
        openai_tools = mcp_tools_to_openai(mcp_list_tools())
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        result = _agent_loop(client, messages, openai_tools)
        print(f"\n{result}")
    else:
        interactive_chat()


if __name__ == "__main__":
    main()
