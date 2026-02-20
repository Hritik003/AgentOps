"""
GitHub PR Review Tool - MCP Server
An MCP server providing GitHub API tools for PR review workflows.
"""

import os
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import Field
from typing import Optional

# Configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Create the MCP server
mcp = Server("github-pr-review")


def get_headers() -> dict:
    """Get headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GitHub-PR-Review-MCP-Server"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def github_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make a request to the GitHub API."""
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = get_headers()
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            **kwargs
        )
        
        if response.status_code >= 400:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.json() if response.text else "Request failed"
            }
        
        return response.json()


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@mcp.tool()
async def list_pull_requests(
    owner: str = Field(description="Repository owner (username or organization)"),
    repo: str = Field(description="Repository name"),
    state: str = Field(default="open", description="PR state: open, closed, or all"),
    sort: str = Field(default="created", description="Sort by: created, updated, or popularity"),
    direction: str = Field(default="desc", description="Sort direction: asc or desc"),
    per_page: int = Field(default=30, description="Results per page (max 100)"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """List pull requests for a repository. Returns PRs with their titles, numbers, states, and authors."""
    params = {
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": per_page,
        "page": page
    }
    
    result = await github_request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
    
    if isinstance(result, list):
        # Format the response for readability
        prs = []
        for pr in result:
            prs.append({
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "author": pr["user"]["login"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "url": pr["html_url"]
            })
        return str(prs)
    
    return str(result)


@mcp.tool()
async def get_pull_request(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number")
) -> str:
    """Get details of a specific pull request including title, description, author, and status."""
    result = await github_request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
    
    if not result.get("error"):
        return str({
            "number": result["number"],
            "title": result["title"],
            "state": result["state"],
            "body": result.get("body", ""),
            "author": result["user"]["login"],
            "base": result["base"]["ref"],
            "head": result["head"]["ref"],
            "mergeable": result.get("mergeable"),
            "additions": result.get("additions"),
            "deletions": result.get("deletions"),
            "changed_files": result.get("changed_files"),
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
            "url": result["html_url"]
        })
    
    return str(result)


@mcp.tool()
async def get_pull_request_files(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
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
async def get_pull_request_commits(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """List all commits in a pull request."""
    params = {"per_page": per_page, "page": page}
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/commits",
        params=params
    )
    
    if isinstance(result, list):
        commits = []
        for c in result:
            commits.append({
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"]
            })
        return str(commits)
    
    return str(result)


@mcp.tool()
async def list_commits(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    sha: Optional[str] = Field(default=None, description="SHA or branch to start listing from"),
    path: Optional[str] = Field(default=None, description="Only commits containing this file path"),
    author: Optional[str] = Field(default=None, description="GitHub username or email"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """List commits in a repository, optionally filtered by branch, path, or author."""
    params = {"per_page": per_page, "page": page}
    if sha:
        params["sha"] = sha
    if path:
        params["path"] = path
    if author:
        params["author"] = author
    
    result = await github_request("GET", f"/repos/{owner}/{repo}/commits", params=params)
    
    if isinstance(result, list):
        commits = []
        for c in result:
            commits.append({
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"]
            })
        return str(commits)
    
    return str(result)


@mcp.tool()
async def get_commit(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    ref: str = Field(description="Commit SHA, branch name, or tag name")
) -> str:
    """Get details of a specific commit including message, author, and files changed."""
    result = await github_request("GET", f"/repos/{owner}/{repo}/commits/{ref}")
    
    if not result.get("error"):
        return str({
            "sha": result["sha"],
            "message": result["commit"]["message"],
            "author": result["commit"]["author"]["name"],
            "date": result["commit"]["author"]["date"],
            "stats": result.get("stats", {}),
            "files": [f["filename"] for f in result.get("files", [])][:20]
        })
    
    return str(result)


@mcp.tool()
async def list_reviews(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """List all reviews on a pull request including their state (approved, changes requested, etc)."""
    params = {"per_page": per_page, "page": page}
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        params=params
    )
    
    if isinstance(result, list):
        reviews = []
        for r in result:
            reviews.append({
                "id": r["id"],
                "user": r["user"]["login"],
                "state": r["state"],
                "body": r.get("body", ""),
                "submitted_at": r.get("submitted_at")
            })
        return str(reviews)
    
    return str(result)


@mcp.tool()
async def get_review(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    review_id: int = Field(description="Review ID")
) -> str:
    """Get details of a specific review on a pull request."""
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}"
    )
    return str(result)


@mcp.tool()
async def create_review(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    event: str = Field(description="Review action: APPROVE, REQUEST_CHANGES, or COMMENT"),
    body: Optional[str] = Field(default=None, description="Review comment text")
) -> str:
    """Create a review on a pull request. Use to approve, request changes, or add a review comment."""
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
    
    if event not in ["APPROVE", "REQUEST_CHANGES", "COMMENT"]:
        return str({"error": f"Invalid event: {event}. Must be APPROVE, REQUEST_CHANGES, or COMMENT"})
    
    payload = {"event": event}
    if body:
        payload["body"] = body
    
    result = await github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json=payload
    )
    return str(result)


@mcp.tool()
async def update_review(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    review_id: int = Field(description="Review ID"),
    body: str = Field(description="New review body text")
) -> str:
    """Update the body text of an existing review."""
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
    
    result = await github_request(
        "PUT",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}",
        json={"body": body}
    )
    return str(result)


@mcp.tool()
async def dismiss_review(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    review_id: int = Field(description="Review ID"),
    message: str = Field(description="Reason for dismissing the review")
) -> str:
    """Dismiss a review on a pull request with a reason."""
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
    
    result = await github_request(
        "PUT",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals",
        json={"message": message}
    )
    return str(result)


@mcp.tool()
async def list_review_comments(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """List all review comments (inline code comments) on a pull request."""
    params = {"per_page": per_page, "page": page}
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/comments",
        params=params
    )
    
    if isinstance(result, list):
        comments = []
        for c in result:
            comments.append({
                "id": c["id"],
                "user": c["user"]["login"],
                "body": c["body"],
                "path": c["path"],
                "line": c.get("line"),
                "created_at": c["created_at"]
            })
        return str(comments)
    
    return str(result)


@mcp.tool()
async def create_review_comment(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    body: str = Field(description="The comment text"),
    commit_id: str = Field(description="SHA of the commit to comment on"),
    path: str = Field(description="Relative path of the file to comment on"),
    line: int = Field(description="Line number in the diff to comment on"),
    side: str = Field(default="RIGHT", description="Side of the diff: LEFT or RIGHT")
) -> str:
    """Create a review comment on a specific line of code in a pull request."""
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
    
    payload = {
        "body": body,
        "commit_id": commit_id,
        "path": path,
        "line": line,
        "side": side
    }
    
    result = await github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/comments",
        json=payload
    )
    return str(result)


@mcp.tool()
async def update_review_comment(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    comment_id: int = Field(description="Comment ID"),
    body: str = Field(description="New comment text")
) -> str:
    """Update an existing review comment."""
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
    
    result = await github_request(
        "PATCH",
        f"/repos/{owner}/{repo}/pulls/comments/{comment_id}",
        json={"body": body}
    )
    return str(result)


@mcp.tool()
async def reply_to_review_comment(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    pull_number: int = Field(description="Pull request number"),
    comment_id: int = Field(description="Comment ID to reply to"),
    body: str = Field(description="Reply text")
) -> str:
    """Reply to an existing review comment thread."""
    if not GITHUB_TOKEN:
        return str({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
    
    result = await github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies",
        json={"body": body}
    )
    return str(result)


@mcp.tool()
async def get_file_contents(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    path: str = Field(description="Path to the file in the repository"),
    ref: Optional[str] = Field(default=None, description="Branch, tag, or commit SHA (default: default branch)")
) -> str:
    """Get the contents of a file from the repository."""
    params = {}
    if ref:
        params["ref"] = ref
    
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/contents/{path}",
        params=params
    )
    
    if not result.get("error") and result.get("content"):
        import base64
        try:
            content = base64.b64decode(result["content"]).decode("utf-8")
            return content
        except:
            return str(result)
    
    return str(result)


@mcp.tool()
async def list_branches(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """List branches in a repository."""
    params = {"per_page": per_page, "page": page}
    result = await github_request("GET", f"/repos/{owner}/{repo}/branches", params=params)
    
    if isinstance(result, list):
        branches = [{"name": b["name"], "protected": b.get("protected", False)} for b in result]
        return str(branches)
    
    return str(result)


@mcp.tool()
async def get_branch(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    branch: str = Field(description="Branch name")
) -> str:
    """Get details of a specific branch."""
    result = await github_request("GET", f"/repos/{owner}/{repo}/branches/{branch}")
    return str(result)


@mcp.tool()
async def compare_commits(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name"),
    base: str = Field(description="Base branch or commit SHA"),
    head: str = Field(description="Head branch or commit SHA"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number")
) -> str:
    """Compare two branches or commits to see the diff and list of commits between them."""
    params = {"per_page": per_page, "page": page}
    result = await github_request(
        "GET",
        f"/repos/{owner}/{repo}/compare/{base}...{head}",
        params=params
    )
    
    if not result.get("error"):
        return str({
            "status": result.get("status"),
            "ahead_by": result.get("ahead_by"),
            "behind_by": result.get("behind_by"),
            "total_commits": result.get("total_commits"),
            "commits": [
                {"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n")[0]}
                for c in result.get("commits", [])[:10]
            ],
            "files_changed": len(result.get("files", []))
        })
    
    return str(result)


@mcp.tool()
async def get_repository(
    owner: str = Field(description="Repository owner"),
    repo: str = Field(description="Repository name")
) -> str:
    """Get information about a repository including description, stars, and default branch."""
    result = await github_request("GET", f"/repos/{owner}/{repo}")
    
    if not result.get("error"):
        return str({
            "name": result["name"],
            "full_name": result["full_name"],
            "description": result.get("description"),
            "default_branch": result["default_branch"],
            "language": result.get("language"),
            "stars": result["stargazers_count"],
            "forks": result["forks_count"],
            "open_issues": result["open_issues_count"],
            "private": result["private"],
            "url": result["html_url"]
        })
    
    return str(result)


# ============================================================================
# SERVER RUNNER
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            mcp.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

