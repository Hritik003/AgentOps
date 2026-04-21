"""
GitHub MCP Server — Workshop Module 2

Three tools that let an AI assistant interact with GitHub:
  1. get_repos        – list repositories for a user/org
  2. get_pull_requests – list pull requests for a repository
  3. write_pull_request_review – post a review comment on a PR

Transport: Streamable HTTP (run with `python server.py`).
  MCP endpoint → http://<host>:<port>/mcp
  Health check → http://<host>:<port>/health
"""

import os
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8000"))

mcp = FastMCP("github-tools")


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


# ---------------------------------------------------------------------------
# Tool 1 — get_repos
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_repos(
    owner: str,
    per_page: int = 10,
    page: int = 1,
) -> str:
    """List public repositories for a GitHub user or organisation."""
    result = await _github(
        "GET",
        f"/users/{owner}/repos",
        params={"per_page": per_page, "page": page, "sort": "updated"},
    )
    if isinstance(result, list):
        repos = [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "description": r.get("description", ""),
                "stars": r["stargazers_count"],
                "language": r.get("language"),
                "url": r["html_url"],
            }
            for r in result
        ]
        return str(repos)
    return str(result)


# ---------------------------------------------------------------------------
# Tool 2 — get_pull_requests
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 10,
    page: int = 1,
) -> str:
    """List pull requests for a repository. State can be open, closed, or all."""
    result = await _github(
        "GET",
        f"/repos/{owner}/{repo}/pulls",
        params={"state": state, "per_page": per_page, "page": page},
    )
    if isinstance(result, list):
        prs = [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "user": pr["user"]["login"],
                "created_at": pr["created_at"],
                "url": pr["html_url"],
            }
            for pr in result
        ]
        return str(prs)
    return str(result)


# ---------------------------------------------------------------------------
# Tool 3 — write_pull_request_review
# ---------------------------------------------------------------------------
@mcp.tool()
async def write_pull_request_review(
    owner: str,
    repo: str,
    pull_number: int,
    body: str,
    event: str = "COMMENT",
) -> str:
    """Post a review on a pull request.

    event must be one of COMMENT, APPROVE, or REQUEST_CHANGES.
    Requires a GITHUB_TOKEN with write access to the repository.
    """
    if not GITHUB_TOKEN:
        return str({"error": "GITHUB_TOKEN is required to write reviews."})
    if event not in ("COMMENT", "APPROVE", "REQUEST_CHANGES"):
        return str({"error": f"Invalid event '{event}'. Use COMMENT, APPROVE, or REQUEST_CHANGES."})

    result = await _github(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json={"event": event, "body": body},
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
