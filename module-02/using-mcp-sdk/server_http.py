"""
GitHub PR Review Tool - MCP Server (Streamable HTTP)
Only 2 tools for code review agent: get_pull_request_files, create_pr_review.

This server is token-agnostic - expects GitHub token in the Authorization header
of incoming requests, similar to how api.github.com works.
"""

import os
import httpx
from contextvars import ContextVar
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

GITHUB_API_BASE = "https://api.github.com"
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8000"))

request_token: ContextVar[str | None] = ContextVar("request_token", default=None)

mcp = FastMCP(name="github-pr-review")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        request_token.set(token)
        return await call_next(request)


def get_github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GitHub-PR-Review-MCP-Server"
    }
    token = request_token.get()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def github_request(method: str, endpoint: str, **kwargs) -> dict:
    url = f"{GITHUB_API_BASE}{endpoint}"
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=get_github_headers(), **kwargs)
        if response.status_code >= 400:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.json() if response.text else "Request failed"
            }
        return response.json()


# ============================================================================
# TOOLS (code review agent: get PR files + add comment)
# ============================================================================

@mcp.tool()
async def get_pull_request_files(
    owner: str,
    repo: str,
    pull_number: int,
    per_page: int = 30,
    page: int = 1
) -> str:
    """Get the list of files changed in a pull request with their diffs and change statistics."""
    params = {"per_page": per_page, "page": page}
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
        params=params
    )
    if isinstance(result, list):
        files = []
        for f in result:
            files.append({
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "changes": f["changes"],
                "patch": f.get("patch", "")[:500] + "..." if len(f.get("patch", "")) > 500 else f.get("patch", "")
            })
        return str(files)
    return str(result)


@mcp.tool()
async def create_pr_review(
    owner: str,
    repo: str,
    pull_number: int,
    event: str,
    body: str = ""
) -> str:
    """Create a review comment on a pull request. Use event COMMENT to add a comment, or APPROVE / REQUEST_CHANGES."""
    if not request_token.get():
        return str({"error": "Authorization header with Bearer token is required for creating PR reviews."})
    if event not in ("COMMENT", "APPROVE", "REQUEST_CHANGES"):
        return str({"error": f"Invalid event: {event}. Must be COMMENT, APPROVE, or REQUEST_CHANGES"})
    payload = {"event": event}
    if body:
        payload["body"] = body
    result = await github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json=payload
    )
    return str(result)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "github-pr-review-mcp"})


if __name__ == "__main__":
    print(f"Starting MCP server on {HOST}:{PORT}")
    print(f"MCP endpoint: http://{HOST}:{PORT}/mcp")
    print(f"Health check: http://{HOST}:{PORT}/health")
    
    app = mcp.http_app(path="/mcp")
    app.add_middleware(AuthMiddleware)
    
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
