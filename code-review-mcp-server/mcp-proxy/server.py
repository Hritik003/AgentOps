"""
MCP Proxy - HTTP server that speaks MCP (JSON-RPC) and proxies tool calls
to the code-review-server HTTP API. No MCP SDK; pure Python.
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

# MCP server identity
SERVER_NAME = "github-pr-review-proxy"
SERVER_VERSION = "1.0.0"


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
        "protocolVersion": "2024-11-05",
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
    """Handle tools/call. Proxy to backend and return MCP content."""
    name = (params or {}).get("name")
    arguments = (params or {}).get("arguments") or {}
    if not name:
        return None, {"code": -32602, "message": "Missing tool name"}
    tool = get_tool_by_name(name)
    if not tool:
        return None, {"code": -32602, "message": f"Unknown tool: {name}"}
    try:
        text = call_tool(BACKEND_BASE_URL, name, arguments)
        return {"content": [{"type": "text", "text": text}], "isError": False}, None
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "isError": True,
        }, None


class MCPProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler: POST body = JSON-RPC request, response = JSON-RPC response."""

    def log_message(self, format, *args):
        # Log to stderr so stdout is not polluted (useful if ever used with stdio)
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/" and parsed.path != "/mcp":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send_jsonrpc_error(None, -32700, "Parse error: empty body")
            return

        try:
            body = self.rfile.read(length).decode("utf-8")
            req = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_jsonrpc_error(None, -32700, f"Parse error: {e}")
            return

        if req.get("jsonrpc") != "2.0":
            self._send_jsonrpc_error(req.get("id"), -32600, "Invalid Request")
            return

        method = req.get("method")
        params = req.get("params")
        req_id = req.get("id")

        # Notifications have no id and get no response
        if req_id is None and method != "notifications/tools/list_changed":
            self.send_response(204)
            self.end_headers()
            return

        if method == "initialize":
            result = handle_initialize(params)
            self._send_jsonrpc_result(req_id, result)
            return

        if method == "initialized":
            # Notification; no response
            self.send_response(204)
            self.end_headers()
            return

        if method == "tools/list":
            result = handle_tools_list(params)
            self._send_jsonrpc_result(req_id, result)
            return

        if method == "tools/call":
            result, err = handle_tools_call(params)
            if err:
                self._send_jsonrpc_error(req_id, err["code"], err["message"])
                return
            self._send_jsonrpc_result(req_id, result)
            return

        self._send_jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    def _send_jsonrpc_result(self, req_id, result):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(make_jsonrpc_response(req_id, result=result)).encode("utf-8"))

    def _send_jsonrpc_error(self, req_id, code, message):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        payload = make_jsonrpc_response(req_id, error={"code": code, "message": message})
        self.wfile.write(json.dumps(payload).encode("utf-8"))


def main():
    port = int(os.environ.get("MCP_PROXY_PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), MCPProxyHandler)
    print(f"MCP Proxy listening on http://0.0.0.0:{port}", file=sys.stderr)
    print(f"Backend: {BACKEND_BASE_URL}", file=sys.stderr)
    print(f"POST JSON-RPC to http://localhost:{port}/ or http://localhost:{port}/mcp", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
