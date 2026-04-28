"""
GitHub MCP Server — Workshop Module 2

Eight tools that let an AI assistant interact with GitHub:
  1. create_branch           – create a new branch
  2. create_or_update_file   – create or update a single file
  3. create_pull_request     – open a new pull request
  4. get_file_contents       – get file or directory contents
  5. list_pull_requests      – list pull requests
  6. pull_request_read       – read PR details, diff, comments, etc.
  7. pull_request_review_write – create/submit/delete reviews, resolve threads
  8. push_files              – push multiple files in one commit

Transport: Streamable HTTP (run with `python server.py`).
  MCP endpoint → http://<host>:<port>/mcp
  Health check → http://<host>:<port>/health
"""

import os
import base64
from typing import Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GITHUB_API_BASE = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8000"))

mcp = FastMCP(
    "github-tools",
    host=HOST,
    port=PORT,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


async def _github(method: str, endpoint: str, **kwargs) -> dict | list:
    """Fire a request against the GitHub REST API and return parsed JSON."""
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"{GITHUB_API_BASE}{endpoint}",
            headers=_headers(),
            **kwargs,
        )
        if resp.status_code >= 400:
            return {"error": resp.status_code, "message": resp.text}
        return resp.json()


async def _graphql(query: str, variables: dict | None = None) -> dict:
    """Execute a GitHub GraphQL query."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_GRAPHQL_URL,
            headers=_headers(),
            json={"query": query, "variables": variables or {}},
        )
        if resp.status_code >= 400:
            return {"error": resp.status_code, "message": resp.text}
        return resp.json()


# ---------------------------------------------------------------------------
# Tool 1 — create_branch
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_branch(
    owner: str,
    repo: str,
    branch: str,
    from_branch: Optional[str] = None,
) -> str:
    """Create a new branch in a GitHub repository."""
    if not GITHUB_TOKEN:
        return str({"error": "GITHUB_TOKEN is required to create branches."})

    if from_branch:
        ref_data = await _github("GET", f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}")
    else:
        repo_data = await _github("GET", f"/repos/{owner}/{repo}")
        if isinstance(repo_data, dict) and "error" in repo_data:
            return str(repo_data)
        default_branch = repo_data.get("default_branch", "main")
        ref_data = await _github("GET", f"/repos/{owner}/{repo}/git/ref/heads/{default_branch}")

    if isinstance(ref_data, dict) and "error" in ref_data:
        return str(ref_data)

    sha = ref_data["object"]["sha"]
    result = await _github(
        "POST",
        f"/repos/{owner}/{repo}/git/refs",
        json={"ref": f"refs/heads/{branch}", "sha": sha},
    )
    return str(result)


# ---------------------------------------------------------------------------
# Tool 2 — create_or_update_file
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_or_update_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str,
    sha: Optional[str] = None,
) -> str:
    """Create or update a single file in a GitHub repository.

    If updating, you should provide the SHA of the file you want to update.
    Use git rev-parse <branch>:<path> to obtain the SHA of the original file.
    SHA MUST be provided for existing file updates.
    """
    if not GITHUB_TOKEN:
        return str({"error": "GITHUB_TOKEN is required to create/update files."})

    encoded_content = base64.b64encode(content.encode()).decode()
    payload: dict = {
        "message": message,
        "content": encoded_content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    result = await _github("PUT", f"/repos/{owner}/{repo}/contents/{path}", json=payload)
    return str(result)


# ---------------------------------------------------------------------------
# Tool 3 — create_pull_request
# ---------------------------------------------------------------------------
@mcp.tool()
async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: Optional[str] = None,
    draft: Optional[bool] = None,
    maintainer_can_modify: Optional[bool] = None,
) -> str:
    """Create a new pull request in a GitHub repository."""
    if not GITHUB_TOKEN:
        return str({"error": "GITHUB_TOKEN is required to create pull requests."})

    payload: dict = {"title": title, "head": head, "base": base}
    if body is not None:
        payload["body"] = body
    if draft is not None:
        payload["draft"] = draft
    if maintainer_can_modify is not None:
        payload["maintainer_can_modify"] = maintainer_can_modify

    result = await _github("POST", f"/repos/{owner}/{repo}/pulls", json=payload)
    return str(result)


# ---------------------------------------------------------------------------
# Tool 4 — get_file_contents
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_file_contents(
    owner: str,
    repo: str,
    path: str = "/",
    ref: Optional[str] = None,
    sha: Optional[str] = None,
) -> str:
    """Get the contents of a file or directory from a GitHub repository."""
    params: dict = {}
    if sha:
        params["ref"] = sha
    elif ref:
        params["ref"] = ref

    result = await _github("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params)

    if isinstance(result, dict) and result.get("type") == "file" and result.get("content"):
        try:
            decoded = base64.b64decode(result["content"]).decode()
            return str({
                "name": result.get("name"),
                "path": result.get("path"),
                "sha": result.get("sha"),
                "size": result.get("size"),
                "type": "file",
                "content": decoded,
            })
        except Exception:
            pass

    if isinstance(result, list):
        entries = [
            {
                "name": e["name"],
                "path": e["path"],
                "type": e["type"],
                "sha": e["sha"],
                "size": e.get("size", 0),
            }
            for e in result
        ]
        return str(entries)

    return str(result)


# ---------------------------------------------------------------------------
# Tool 5 — list_pull_requests
# ---------------------------------------------------------------------------
@mcp.tool()
async def list_pull_requests(
    owner: str,
    repo: str,
    state: Optional[str] = None,
    head: Optional[str] = None,
    base: Optional[str] = None,
    sort: Optional[str] = None,
    direction: Optional[str] = None,
    per_page: Optional[int] = None,
    page: Optional[int] = None,
) -> str:
    """List pull requests in a GitHub repository.

    State can be open, closed, or all.
    Sort by created, updated, popularity, or long-running.
    """
    params: dict = {}
    if state:
        params["state"] = state
    if head:
        params["head"] = head
    if base:
        params["base"] = base
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if per_page is not None:
        params["per_page"] = per_page
    if page is not None:
        params["page"] = page

    result = await _github("GET", f"/repos/{owner}/{repo}/pulls", params=params)
    if isinstance(result, list):
        prs = [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "user": pr["user"]["login"],
                "created_at": pr["created_at"],
                "url": pr["html_url"],
                "head": pr["head"]["ref"],
                "base": pr["base"]["ref"],
                "draft": pr.get("draft", False),
            }
            for pr in result
        ]
        return str(prs)
    return str(result)


# ---------------------------------------------------------------------------
# Tool 6 — pull_request_read
# ---------------------------------------------------------------------------
@mcp.tool()
async def pull_request_read(
    method: str,
    owner: str,
    repo: str,
    pull_number: int,
    per_page: Optional[int] = None,
    page: Optional[int] = None,
) -> str:
    """Get information on a specific pull request in a GitHub repository.

    method must be one of:
      - get: Get details of a specific pull request.
      - get_diff: Get the diff of a pull request.
      - get_status: Get combined commit status of the head commit.
      - get_files: Get the list of files changed.
      - get_review_comments: Get review threads on a pull request.
      - get_reviews: Get the reviews on a pull request.
      - get_comments: Get comments on a pull request.
      - get_check_runs: Get check runs for the head commit.
    """
    valid_methods = {
        "get", "get_diff", "get_status", "get_files",
        "get_review_comments", "get_reviews", "get_comments", "get_check_runs",
    }
    if method not in valid_methods:
        return str({"error": f"Invalid method '{method}'. Must be one of: {', '.join(sorted(valid_methods))}"})

    params: dict = {}
    if per_page is not None:
        params["per_page"] = per_page
    if page is not None:
        params["page"] = page

    if method == "get":
        result = await _github("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
        return str(result)

    if method == "get_diff":
        async with httpx.AsyncClient() as client:
            headers = _headers()
            headers["Accept"] = "application/vnd.github.diff"
            resp = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pull_number}",
                headers=headers,
            )
            if resp.status_code >= 400:
                return str({"error": resp.status_code, "message": resp.text})
            return resp.text

    if method == "get_status":
        pr_data = await _github("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
        if isinstance(pr_data, dict) and "error" in pr_data:
            return str(pr_data)
        head_sha = pr_data["head"]["sha"]
        result = await _github("GET", f"/repos/{owner}/{repo}/commits/{head_sha}/status")
        return str(result)

    if method == "get_files":
        result = await _github(
            "GET", f"/repos/{owner}/{repo}/pulls/{pull_number}/files", params=params,
        )
        return str(result)

    if method == "get_review_comments":
        result = await _github(
            "GET", f"/repos/{owner}/{repo}/pulls/{pull_number}/comments", params=params,
        )
        return str(result)

    if method == "get_reviews":
        result = await _github(
            "GET", f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews", params=params,
        )
        return str(result)

    if method == "get_comments":
        result = await _github(
            "GET", f"/repos/{owner}/{repo}/issues/{pull_number}/comments", params=params,
        )
        return str(result)

    if method == "get_check_runs":
        pr_data = await _github("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
        if isinstance(pr_data, dict) and "error" in pr_data:
            return str(pr_data)
        head_sha = pr_data["head"]["sha"]
        result = await _github(
            "GET", f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs", params=params,
        )
        return str(result)

    return str({"error": "Unhandled method"})


# ---------------------------------------------------------------------------
# Tool 7 — pull_request_review_write
# ---------------------------------------------------------------------------
@mcp.tool()
async def pull_request_review_write(
    method: str,
    owner: str,
    repo: str,
    pull_number: int,
    body: Optional[str] = None,
    event: Optional[str] = None,
    commit_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> str:
    """Create and/or submit, delete review of a pull request.

    method must be one of:
      - create: Create a new review. If event is provided, review is submitted immediately.
      - submit_pending: Submit an existing pending review.
      - delete_pending: Delete an existing pending review.
      - resolve_thread: Resolve a review thread (requires thread_id).
      - unresolve_thread: Unresolve a review thread (requires thread_id).
    """
    if not GITHUB_TOKEN:
        return str({"error": "GITHUB_TOKEN is required to write reviews."})

    valid_methods = {"create", "submit_pending", "delete_pending", "resolve_thread", "unresolve_thread"}
    if method not in valid_methods:
        return str({"error": f"Invalid method '{method}'. Must be one of: {', '.join(sorted(valid_methods))}"})

    if event and event not in ("APPROVE", "REQUEST_CHANGES", "COMMENT"):
        return str({"error": f"Invalid event '{event}'. Use APPROVE, REQUEST_CHANGES, or COMMENT."})

    if method == "create":
        payload: dict = {}
        if body:
            payload["body"] = body
        if event:
            payload["event"] = event
        if commit_id:
            payload["commit_id"] = commit_id
        result = await _github(
            "POST", f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews", json=payload,
        )
        return str(result)

    if method == "submit_pending":
        reviews = await _github("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews")
        if isinstance(reviews, dict) and "error" in reviews:
            return str(reviews)
        pending = [r for r in reviews if r.get("state") == "PENDING"]
        if not pending:
            return str({"error": "No pending review found for this pull request."})
        review_id = pending[0]["id"]
        payload = {}
        if body:
            payload["body"] = body
        if event:
            payload["event"] = event
        else:
            payload["event"] = "COMMENT"
        result = await _github(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events",
            json=payload,
        )
        return str(result)

    if method == "delete_pending":
        reviews = await _github("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews")
        if isinstance(reviews, dict) and "error" in reviews:
            return str(reviews)
        pending = [r for r in reviews if r.get("state") == "PENDING"]
        if not pending:
            return str({"error": "No pending review found for this pull request."})
        review_id = pending[0]["id"]
        result = await _github(
            "DELETE", f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}",
        )
        return str(result)

    if method in ("resolve_thread", "unresolve_thread"):
        if not thread_id:
            return str({"error": f"thread_id is required for {method}."})
        mutation = "resolveReviewThread" if method == "resolve_thread" else "unresolveReviewThread"
        query = f"""
        mutation {{
            {mutation}(input: {{threadId: "{thread_id}"}}) {{
                thread {{
                    id
                    isResolved
                }}
            }}
        }}
        """
        result = await _graphql(query)
        return str(result)

    return str({"error": "Unhandled method"})


# ---------------------------------------------------------------------------
# Tool 8 — push_files
# ---------------------------------------------------------------------------
@mcp.tool()
async def push_files(
    owner: str,
    repo: str,
    branch: str,
    files: list[dict],
    message: str,
) -> str:
    """Push multiple files to a GitHub repository in a single commit.

    files should be a list of objects with 'path' and 'content' keys.
    """
    if not GITHUB_TOKEN:
        return str({"error": "GITHUB_TOKEN is required to push files."})

    ref_data = await _github("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if isinstance(ref_data, dict) and "error" in ref_data:
        return str(ref_data)
    base_sha = ref_data["object"]["sha"]

    base_commit = await _github("GET", f"/repos/{owner}/{repo}/git/commits/{base_sha}")
    if isinstance(base_commit, dict) and "error" in base_commit:
        return str(base_commit)
    base_tree_sha = base_commit["tree"]["sha"]

    tree_items = []
    for f in files:
        blob = await _github(
            "POST",
            f"/repos/{owner}/{repo}/git/blobs",
            json={"content": f["content"], "encoding": "utf-8"},
        )
        if isinstance(blob, dict) and "error" in blob:
            return str(blob)
        tree_items.append({
            "path": f["path"],
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })

    tree = await _github(
        "POST",
        f"/repos/{owner}/{repo}/git/trees",
        json={"base_tree": base_tree_sha, "tree": tree_items},
    )
    if isinstance(tree, dict) and "error" in tree:
        return str(tree)

    commit = await _github(
        "POST",
        f"/repos/{owner}/{repo}/git/commits",
        json={
            "message": message,
            "tree": tree["sha"],
            "parents": [base_sha],
        },
    )
    if isinstance(commit, dict) and "error" in commit:
        return str(commit)

    result = await _github(
        "PATCH",
        f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
        json={"sha": commit["sha"]},
    )
    return str(result)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "github-tools-mcp"})


# ---------------------------------------------------------------------------
# Entry-point — Streamable HTTP transport
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    print(f"Starting MCP server on {HOST}:{PORT}")
    print(f"  MCP endpoint: http://{HOST}:{PORT}/mcp")
    print(f"  Health check: http://{HOST}:{PORT}/health")

    app = mcp.streamable_http_app()
    uvicorn.run(app, host=HOST, port=PORT)
