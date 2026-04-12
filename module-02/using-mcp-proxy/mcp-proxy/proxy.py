"""
Proxy layer: map MCP tool calls to code-review-server HTTP API requests.
Tools: get_pull_request_files, create_pr_review.

call_tool returns:
- str: single response (one SSE event). Current behavior for all tools.
- Iterable[str]: stream of chunks (generator or list). Yield/return chunks as
  the backend produces them; the server forwards each chunk immediately (one
  SSE event per chunk) without collecting all first.
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Any, Dict, Iterator, List, Optional, Union


def _request(
    base_url: str,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> tuple:
    """Perform HTTP request to the backend. Returns (status_code, body)."""
    url = base_url.rstrip("/") + path
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)

    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else "{}"
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as e:
        return -1, {"error": str(e)}


def _request_stream(
    base_url: str,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    chunk_size: int = 4096,
) -> Iterator[str]:
    """
    Perform HTTP request and yield response body in chunks. Use when the backend
    streams; the server will forward each chunk immediately as one SSE event.
    """
    url = base_url.rstrip("/") + path
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30.0, context=ssl.create_default_context()) as resp:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                yield chunk.decode("utf-8", errors="replace")
    except Exception:
        yield json.dumps({"error": "Stream request failed"})


def call_tool(backend_base_url: str, tool_name: str, arguments: Dict[str, Any]) -> Union[str, List[str], Iterator[str]]:
    """
    Execute the given tool by calling the code-review-server HTTP API.
    Returns str for a single response (one SSE event), or an iterable of
    chunks (list or generator) to stream; each chunk is sent as soon as it's
    received (no buffering).
    """
    args = arguments or {}
    base = backend_base_url.rstrip("/")

    if tool_name == "get_pull_request_files":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/files",
            params=params,
        )
        if status == 200 and isinstance(data, list):
            out = []
            for f in data:
                patch = (f.get("patch") or "")[:500]
                if len(f.get("patch") or "") > 500:
                    patch += "..."
                out.append({
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                    "changes": f.get("changes"),
                    "patch": patch,
                })
            return json.dumps(out, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "create_pr_review":
        payload = {"event": args["event"]}
        if args.get("body"):
            payload["body"] = args["body"]
        status, data = _request(
            base, "POST",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/reviews",
            json_body=payload,
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
