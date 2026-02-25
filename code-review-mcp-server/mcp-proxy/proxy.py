"""
Proxy layer: map MCP tool calls to code-review-server HTTP API requests.
Uses only stdlib (urllib) to call the backend. No MCP SDK.
"""

import json
import base64
import urllib.request
import urllib.error
import ssl
from typing import Any, Dict, Optional


def _request(
    base_url: str,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> tuple:
    """
    Perform HTTP request to the backend. Returns (status_code, body).
    body is parsed as JSON when possible, else raw text.
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


def call_tool(backend_base_url: str, tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute the given tool by calling the code-review-server HTTP API.
    Returns a string suitable for MCP text content (or error message).
    """
    args = arguments or {}
    base = backend_base_url.rstrip("/")

    # Map each tool to backend path and method
    if tool_name == "get_repository":
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}")
        if status == 200 and isinstance(data, dict) and "error" not in data:
            return json.dumps({
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "default_branch": data.get("default_branch"),
                "language": data.get("language"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "private": data.get("private"),
                "url": data.get("html_url"),
            }, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "list_pull_requests":
        params = {
            "state": args.get("state", "open"),
            "sort": args.get("sort", "created"),
            "direction": args.get("direction", "desc"),
            "per_page": args.get("per_page", 30),
            "page": args.get("page", 1),
        }
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}/pulls", params=params)
        if status == 200 and isinstance(data, list):
            out = []
            for pr in data:
                out.append({
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "author": pr.get("user", {}).get("login"),
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                    "url": pr.get("html_url"),
                })
            return json.dumps(out, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "get_pull_request":
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}")
        if status == 200 and isinstance(data, dict) and "error" not in data:
            return json.dumps({
                "number": data.get("number"),
                "title": data.get("title"),
                "state": data.get("state"),
                "body": data.get("body", ""),
                "author": data.get("user", {}).get("login"),
                "base": data.get("base", {}).get("ref"),
                "head": data.get("head", {}).get("ref"),
                "mergeable": data.get("mergeable"),
                "additions": data.get("additions"),
                "deletions": data.get("deletions"),
                "changed_files": data.get("changed_files"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "url": data.get("html_url"),
            }, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

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

    if tool_name == "get_pull_request_commits":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/commits",
            params=params,
        )
        if status == 200 and isinstance(data, list):
            out = []
            for c in data:
                commit = c.get("commit", {})
                author = commit.get("author", {})
                out.append({
                    "sha": (c.get("sha") or "")[:7],
                    "message": (commit.get("message") or "").split("\n")[0],
                    "author": author.get("name"),
                    "date": author.get("date"),
                })
            return json.dumps(out, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "list_commits":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        for k in ("sha", "path", "author"):
            if args.get(k):
                params[k] = args[k]
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}/commits", params=params)
        if status == 200 and isinstance(data, list):
            out = []
            for c in data:
                commit = c.get("commit", {})
                author = commit.get("author", {})
                out.append({
                    "sha": (c.get("sha") or "")[:7],
                    "message": (commit.get("message") or "").split("\n")[0],
                    "author": author.get("name"),
                    "date": author.get("date"),
                })
            return json.dumps(out, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "get_commit":
        ref = args["ref"]
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}/commits/{ref}")
        if status == 200 and isinstance(data, dict) and "error" not in data:
            commit = data.get("commit", {})
            return json.dumps({
                "sha": data.get("sha"),
                "message": commit.get("message"),
                "author": commit.get("author", {}).get("name"),
                "date": commit.get("author", {}).get("date"),
                "stats": data.get("stats", {}),
                "files": [f.get("filename") for f in data.get("files", [])][:20],
            }, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "list_reviews":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/reviews",
            params=params,
        )
        if status == 200 and isinstance(data, list):
            out = [{"id": r.get("id"), "user": (r.get("user") or {}).get("login"), "state": r.get("state"), "body": r.get("body", ""), "submitted_at": r.get("submitted_at")} for r in data]
            return json.dumps(out, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "get_review":
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/reviews/{args['review_id']}",
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "create_review":
        payload = {"event": args["event"]}
        if args.get("body"):
            payload["body"] = args["body"]
        status, data = _request(
            base, "POST",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/reviews",
            json_body=payload,
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "update_review":
        status, data = _request(
            base, "PUT",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/reviews/{args['review_id']}",
            json_body={"body": args["body"]},
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "dismiss_review":
        status, data = _request(
            base, "PUT",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/reviews/{args['review_id']}/dismiss",
            json_body={"message": args["message"]},
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "list_review_comments":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/comments",
            params=params,
        )
        if status == 200 and isinstance(data, list):
            out = [{"id": c.get("id"), "user": (c.get("user") or {}).get("login"), "body": c.get("body"), "path": c.get("path"), "line": c.get("line"), "created_at": c.get("created_at")} for c in data]
            return json.dumps(out, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "create_review_comment":
        payload = {
            "body": args["body"],
            "commit_id": args["commit_id"],
            "path": args["path"],
            "line": args["line"],
            "side": args.get("side", "RIGHT"),
        }
        status, data = _request(
            base, "POST",
            f"/repos/{args['owner']}/{args['repo']}/pulls/{args['pull_number']}/comments",
            json_body=payload,
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "update_review_comment":
        status, data = _request(
            base, "PATCH",
            f"/repos/{args['owner']}/{args['repo']}/pulls/comments/{args['comment_id']}",
            json_body={"body": args["body"]},
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "reply_to_review_comment":
        status, data = _request(
            base, "POST",
            f"/repos/{args['owner']}/{args['repo']}/pulls/comments/{args['comment_id']}/replies",
            json_body={"body": args["body"]},
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "list_issue_comments":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/issues/{args['issue_number']}/comments",
            params=params,
        )
        return json.dumps(data) if isinstance(data, (list, dict)) else str(data)

    if tool_name == "create_issue_comment":
        status, data = _request(
            base, "POST",
            f"/repos/{args['owner']}/{args['repo']}/issues/{args['issue_number']}/comments",
            json_body={"body": args["body"]},
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "update_issue_comment":
        status, data = _request(
            base, "PATCH",
            f"/repos/{args['owner']}/{args['repo']}/issues/comments/{args['comment_id']}",
            json_body={"body": args["body"]},
        )
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "get_file_contents":
        params = {}
        if args.get("ref"):
            params["ref"] = args["ref"]
        path = args["path"].lstrip("/")
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/contents/{path}",
            params=params if params else None,
        )
        if status == 200 and isinstance(data, dict) and data.get("content"):
            try:
                return base64.b64decode(data["content"]).decode("utf-8")
            except Exception:
                pass
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "list_branches":
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}/branches", params=params)
        if status == 200 and isinstance(data, list):
            return json.dumps([{"name": b.get("name"), "protected": b.get("protected", False)} for b in data], indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "get_branch":
        branch = args["branch"]
        status, data = _request(base, "GET", f"/repos/{args['owner']}/{args['repo']}/branches/{branch}")
        return json.dumps(data) if isinstance(data, dict) else str(data)

    if tool_name == "compare_commits":
        basehead = f"{args['base']}...{args['head']}"
        params = {"per_page": args.get("per_page", 30), "page": args.get("page", 1)}
        status, data = _request(
            base, "GET",
            f"/repos/{args['owner']}/{args['repo']}/compare/{basehead}",
            params=params,
        )
        if status == 200 and isinstance(data, dict) and "error" not in data:
            return json.dumps({
                "status": data.get("status"),
                "ahead_by": data.get("ahead_by"),
                "behind_by": data.get("behind_by"),
                "total_commits": data.get("total_commits"),
                "commits": [{"sha": c.get("sha", "")[:7], "message": (c.get("commit") or {}).get("message", "").split("\n")[0]} for c in data.get("commits", [])[:10]],
                "files_changed": len(data.get("files", [])),
            }, indent=2)
        return json.dumps(data) if isinstance(data, dict) else str(data)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
