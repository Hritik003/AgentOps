"""
GitHub PR Review Tool - MCP Server (stdio)
Only 2 tools for code review agent: get_pull_request_files, create_issue_comment.
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

mcp = FastMCP("github-pr-review")


def get_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GitHub-PR-Review-MCP-Server"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def github_request(method: str, endpoint: str, **kwargs) -> dict:
    url = f"{GITHUB_API_BASE}{endpoint}"
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=get_headers(), **kwargs)
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
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
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


if __name__ == "__main__":
    mcp.run()
