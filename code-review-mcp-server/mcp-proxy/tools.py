"""
Tool definitions for the MCP proxy.
Each tool maps to one or more HTTP API calls on the code-review-server (backend).
"""
from __future__ import annotations

# Tool definitions: name, description, inputSchema (JSON Schema), and executor key for dispatch
TOOLS = [
    {
        "name": "get_repository",
        "description": "Get information about a repository including description, stars, and default branch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
            },
            "required": ["owner", "repo"],
        },
    },
    {
        "name": "list_pull_requests",
        "description": "List pull requests for a repository. Returns PRs with their titles, numbers, states, and authors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
                "state": {"type": "string", "description": "PR state: open, closed, or all", "default": "open"},
                "sort": {"type": "string", "description": "Sort by: created, updated, or popularity", "default": "created"},
                "direction": {"type": "string", "description": "Sort direction: asc or desc", "default": "desc"},
                "per_page": {"type": "integer", "description": "Results per page (max 100)", "default": 30},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["owner", "repo"],
        },
    },
    {
        "name": "get_pull_request",
        "description": "Get details of a specific pull request including title, description, author, and status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pull_number"],
        },
    },
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
        "name": "get_pull_request_commits",
        "description": "List all commits in a pull request.",
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
        "name": "list_commits",
        "description": "List commits in a repository, optionally filtered by branch, path, or author.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "sha": {"type": "string", "description": "SHA or branch to start listing from"},
                "path": {"type": "string", "description": "Only commits containing this file path"},
                "author": {"type": "string", "description": "GitHub username or email"},
                "per_page": {"type": "integer", "description": "Results per page", "default": 30},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["owner", "repo"],
        },
    },
    {
        "name": "get_commit",
        "description": "Get details of a specific commit including message, author, and files changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "ref": {"type": "string", "description": "Commit SHA, branch name, or tag name"},
            },
            "required": ["owner", "repo", "ref"],
        },
    },
    {
        "name": "list_reviews",
        "description": "List all reviews on a pull request including their state (approved, changes requested, etc).",
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
        "name": "get_review",
        "description": "Get details of a specific review on a pull request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "review_id": {"type": "integer", "description": "Review ID"},
            },
            "required": ["owner", "repo", "pull_number", "review_id"],
        },
    },
    {
        "name": "create_review",
        "description": "Create a review on a pull request. Use to approve, request changes, or add a review comment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "event": {"type": "string", "description": "Review action: APPROVE, REQUEST_CHANGES, or COMMENT"},
                "body": {"type": "string", "description": "Review comment text"},
            },
            "required": ["owner", "repo", "pull_number", "event"],
        },
    },
    {
        "name": "update_review",
        "description": "Update the body text of an existing review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "review_id": {"type": "integer", "description": "Review ID"},
                "body": {"type": "string", "description": "New review body text"},
            },
            "required": ["owner", "repo", "pull_number", "review_id", "body"],
        },
    },
    {
        "name": "dismiss_review",
        "description": "Dismiss a review on a pull request with a reason.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "review_id": {"type": "integer", "description": "Review ID"},
                "message": {"type": "string", "description": "Reason for dismissing the review"},
            },
            "required": ["owner", "repo", "pull_number", "review_id", "message"],
        },
    },
    {
        "name": "list_review_comments",
        "description": "List all review comments (inline code comments) on a pull request.",
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
        "name": "create_review_comment",
        "description": "Create a review comment on a specific line of code in a pull request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
                "body": {"type": "string", "description": "The comment text"},
                "commit_id": {"type": "string", "description": "SHA of the commit to comment on"},
                "path": {"type": "string", "description": "Relative path of the file to comment on"},
                "line": {"type": "integer", "description": "Line number in the diff to comment on"},
                "side": {"type": "string", "description": "Side of the diff: LEFT or RIGHT", "default": "RIGHT"},
            },
            "required": ["owner", "repo", "pull_number", "body", "commit_id", "path", "line"],
        },
    },
    {
        "name": "update_review_comment",
        "description": "Update an existing review comment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "comment_id": {"type": "integer", "description": "Comment ID"},
                "body": {"type": "string", "description": "New comment text"},
            },
            "required": ["owner", "repo", "comment_id", "body"],
        },
    },
    {
        "name": "reply_to_review_comment",
        "description": "Reply to an existing review comment thread.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "comment_id": {"type": "integer", "description": "Comment ID to reply to"},
                "body": {"type": "string", "description": "Reply text"},
            },
            "required": ["owner", "repo", "comment_id", "body"],
        },
    },
    {
        "name": "list_issue_comments",
        "description": "List comments on an issue or pull request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue or PR number"},
                "per_page": {"type": "integer", "description": "Results per page", "default": 30},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["owner", "repo", "issue_number"],
        },
    },
    {
        "name": "create_issue_comment",
        "description": "Create a comment on an issue or pull request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue or PR number"},
                "body": {"type": "string", "description": "The comment text"},
            },
            "required": ["owner", "repo", "issue_number", "body"],
        },
    },
    {
        "name": "update_issue_comment",
        "description": "Update an issue/PR comment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "comment_id": {"type": "integer", "description": "Comment ID"},
                "body": {"type": "string", "description": "The new comment text"},
            },
            "required": ["owner", "repo", "comment_id", "body"],
        },
    },
    {
        "name": "get_file_contents",
        "description": "Get the contents of a file from the repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "Path to the file in the repository"},
                "ref": {"type": "string", "description": "Branch, tag, or commit SHA (default: default branch)"},
            },
            "required": ["owner", "repo", "path"],
        },
    },
    {
        "name": "list_branches",
        "description": "List branches in a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "per_page": {"type": "integer", "description": "Results per page", "default": 30},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["owner", "repo"],
        },
    },
    {
        "name": "get_branch",
        "description": "Get details of a specific branch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "branch": {"type": "string", "description": "Branch name"},
            },
            "required": ["owner", "repo", "branch"],
        },
    },
    {
        "name": "compare_commits",
        "description": "Compare two branches or commits to see the diff and list of commits between them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "base": {"type": "string", "description": "Base branch or commit SHA"},
                "head": {"type": "string", "description": "Head branch or commit SHA"},
                "per_page": {"type": "integer", "description": "Results per page", "default": 30},
                "page": {"type": "integer", "description": "Page number", "default": 1},
            },
            "required": ["owner", "repo", "base", "head"],
        },
    },
]


def get_tool_by_name(name: str) -> dict | None:
    """Return tool definition for the given name, or None."""
    for t in TOOLS:
        if t["name"] == name:
            return t
    return None
