"""
Tool definitions for the MCP proxy (code review agent).
Tools: get pull request files, create PR review comment.
"""
from __future__ import annotations

TOOLS = [
    {
        "name": "get_pull_request_files",
        "description": "Get the list of files changed in a pull request with their diffs and change statistics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "per_page": {"type": "integer", "description": "Results per page", "default": 30},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["owner", "repo", "pull_number"],
        },
    },
    {
        "name": "create_pr_review",
        "description": "Create a review comment on a pull request (PR review). Use event COMMENT to add a comment, or APPROVE / REQUEST_CHANGES.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "event": {"type": "string", "description": "COMMENT, APPROVE, or REQUEST_CHANGES"},
                "body": {"type": "string", "description": "Review comment text"},
            },
            "required": ["owner", "repo", "pull_number", "event"],
        },
    },
]


def get_tool_by_name(name: str) -> dict | None:
    """Return tool definition for the given name, or None."""
    for t in TOOLS:
        if t["name"] == name:
            return t
    return None
