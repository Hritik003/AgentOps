"""
MCP Proxy - Streamable HTTP server that speaks MCP (JSON-RPC) and proxies
tool calls to the code-review-server HTTP API. No MCP SDK; pure Python.

Implements the MCP Streamable HTTP transport: single endpoint supports
POST (JSON-RPC) and GET (SSE stream). Notifications get 202 Accepted.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from tools import TOOLS, get_tool_by_name
from proxy import call_tool

# Backend code-review-server base URL (e.g. http://localhost:5000)
BACKEND_BASE_URL = os.environ.get("CODE_REVIEW_SERVER_URL", "http://localhost:5000")

# MCP endpoint path (Streamable HTTP: single endpoint for POST and GET)
MCP_PATH = "/mcp"

# MCP server identity
SERVER_NAME = "github-pr-review-proxy"
SERVER_VERSION = "1.0.0"

# Protocol version we support (reported in initialize)
PROTOCOL_VERSION = "2024-11-05"


def _is_mcp_endpoint(path: str) -> bool:
    p = path.rstrip("/") or "/"
    return p == "/mcp" or p == "/"


def make_jsonrpc_response(id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    return out


def handle_initialize(params):
    """Handle initialize request. Return server capabilities."""
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {
            "tools": {"listChanged": True},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
    }


def handle_tools_list(params):
    """Handle tools/list. Return list of tool definitions."""
    return {"tools": TOOLS}


def handle_tools_call(params):
    """
    Handle tools/call. Proxy to backend and return MCP content.
    Backend (call_tool) may return str → one event, or an iterable of chunks
    (list or generator) → stream one SSE event per chunk as received.
    """
    name = (params or {}).get("name")
    arguments = (params or {}).get("arguments") or {}
    if not name:
        return None, {"code": -32602, "message": "Missing tool name"}
    tool = get_tool_by_name(name)
    if not tool:
        return None, {"code": -32602, "message": f"Unknown tool: {name}"}
    try:
        out = call_tool(BACKEND_BASE_URL, name, arguments)
        # str → single event (dict); iterable (list or generator) → stream chunks as received
        if isinstance(out, str):
            return {"content": [{"type": "text", "text": out}], "isError": False}, None
        return out, None  # iterable of chunks; server sends one SSE event per chunk, flush each
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "isError": True,
        }, None


class MCPProxyHandler(BaseHTTPRequestHandler):
    """
    Streamable HTTP transport: POST = JSON-RPC in, response = SSE (one or more events).
    tools/call: if backend returns str → one event; if list[str] → multiple events.
    GET = SSE stream. Notifications (no id) get 202 Accepted.
    """

    def log_message(self, format, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def _send_202_accepted(self):
        """Streamable HTTP: server accepts notification/response, no body."""
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        if not _is_mcp_endpoint(self.path):
            self.send_response(404)
            self.end_headers()
            return

        # Streamable HTTP: GET returns SSE stream (minimal: one event then close)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Send one SSE event so client has a valid stream (id primes for Last-Event-ID resume)
        try:
            self.wfile.write(b"id: 0\n")
            self.wfile.write(b"data: {}\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not _is_mcp_endpoint(self.path):
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send_jsonrpc_error_sse(None, -32700, "Parse error: empty body")
            return

        try:
            body = self.rfile.read(length).decode("utf-8")
            req = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_jsonrpc_error_sse(None, -32700, f"Parse error: {e}")
            return

        if req.get("jsonrpc") != "2.0":
            self._send_jsonrpc_error_sse(req.get("id"), -32600, "Invalid Request")
            return

        method = req.get("method")
        params = req.get("params")
        req_id = req.get("id")

        # Streamable HTTP: notifications (no id) → 202 Accepted, no body
        if req_id is None:
            if method == "initialized" or method == "notifications/tools/list_changed":
                self._send_202_accepted()
                return
            # Other notifications: still 202
            self._send_202_accepted()
            return

        # JSON-RPC request: return 200 + text/event-stream (SSE) with one event
        if method == "initialize":
            result = handle_initialize(params)
            self._send_jsonrpc_result_sse(req_id, result)
            return

        if method == "tools/list":
            result = handle_tools_list(params)
            self._send_jsonrpc_result_sse(req_id, result)
            return

        if method == "tools/call":
            result, err = handle_tools_call(params)
            if err:
                self._send_jsonrpc_error_sse(req_id, err["code"], err["message"])
                return
            if isinstance(result, dict):
                self._send_jsonrpc_result_sse(req_id, result)
                return
            # Iterable of chunks (list or generator): stream one SSE event per chunk as received
            self._send_sse_events_chunks(req_id, result)
            return
        self._send_jsonrpc_error_sse(req_id, -32601, f"Method not found: {method}")

    def _send_sse_headers(self):
        """Send 200 and SSE headers (call once before writing multiple events)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _write_sse_event(self, data: dict, event_id: str = None):
        """Write one SSE event to the stream (no HTTP headers)."""
        payload = json.dumps(data)
        self.wfile.write(b"event: message\n")
        if event_id is not None:
            self.wfile.write(f"id: {event_id}\n".encode("utf-8"))
        for line in payload.split("\n"):
            self.wfile.write(f"data: {line}\n".encode("utf-8"))
        self.wfile.write(b"\n")

    def _send_sse_event(self, data: dict, event_id: str = None):
        """Send response with one SSE event (headers + event)."""
        self._send_sse_headers()
        self._write_sse_event(data, event_id)
        try:
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_sse_events_chunks(self, req_id, chunks):
        """
        Send multiple SSE events (one per chunk). chunks is an iterable (list or generator).
        Flush after each event so the client receives chunks as they're produced.
        """
        self._send_sse_headers()
        try:
            for i, chunk in enumerate(chunks):
                payload = make_jsonrpc_response(
                    req_id,
                    result={"content": [{"type": "text", "text": chunk}], "isError": False},
                )
                self._write_sse_event(payload, event_id=f"{req_id}-{i}" if req_id is not None else str(i))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_jsonrpc_result_sse(self, req_id, result):
        payload = make_jsonrpc_response(req_id, result=result)
        self._send_sse_event(payload, event_id=str(req_id) if req_id is not None else None)

    def _send_jsonrpc_error_sse(self, req_id, code, message):
        payload = make_jsonrpc_response(req_id, error={"code": code, "message": message})
        self._send_sse_event(payload, event_id=str(req_id) if req_id is not None else None)



def main():
    port = int(os.environ.get("MCP_PROXY_PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), MCPProxyHandler)
    print(f"MCP Proxy (streamable HTTP) on http://0.0.0.0:{port}", file=sys.stderr)
    print(f"MCP endpoint: http://localhost:{port}{MCP_PATH}", file=sys.stderr)
    print(f"Backend: {BACKEND_BASE_URL}", file=sys.stderr)
    print(f"POST JSON-RPC to endpoint; GET for SSE stream.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
