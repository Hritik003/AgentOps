"""
GitHub PR Review Tool - HTTP Server
A Flask-based HTTP server providing GitHub API endpoints for PR review workflows.
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from functools import wraps

app = Flask(__name__)
CORS(app)

# Configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def get_headers():
    """Get headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers

def github_request(method, endpoint, **kwargs):
    """Make a request to the GitHub API."""
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = get_headers()
    
    response = requests.request(
        method,
        url,
        headers=headers,
        **kwargs
    )
    return response

def require_token(f):
    """Decorator to require GitHub token for certain endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not GITHUB_TOKEN:
            return jsonify({
                "error": "GitHub token not configured",
                "message": "Set GITHUB_TOKEN environment variable"
            }), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "token_configured": bool(GITHUB_TOKEN)
    })

# ============================================================================
# REPOSITORY INFO
# ============================================================================

@app.route("/repos/<owner>/<repo>", methods=["GET"])
def get_repository(owner, repo):
    """Get repository information."""
    response = github_request("GET", f"/repos/{owner}/{repo}")
    return jsonify(response.json()), response.status_code

# ============================================================================
# PULL REQUESTS
# ============================================================================

@app.route("/repos/<owner>/<repo>/pulls", methods=["GET"])
def list_pull_requests(owner, repo):
    """
    List pull requests for a repository.
    
    Query params:
        - state: open, closed, all (default: open)
        - sort: created, updated, popularity (default: created)
        - direction: asc, desc (default: desc)
        - per_page: results per page (default: 30, max: 100)
        - page: page number (default: 1)
    """
    params = {
        "state": request.args.get("state", "open"),
        "sort": request.args.get("sort", "created"),
        "direction": request.args.get("direction", "desc"),
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    
    response = github_request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>", methods=["GET"])
def get_pull_request(owner, repo, pull_number):
    """Get a specific pull request."""
    response = github_request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/files", methods=["GET"])
def get_pull_request_files(owner, repo, pull_number):
    """
    Get files changed in a pull request.
    Shows the diff for each file.
    """
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET", 
        f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
        params=params
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/commits", methods=["GET"])
def get_pull_request_commits(owner, repo, pull_number):
    """List commits on a pull request."""
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/commits",
        params=params
    )
    return jsonify(response.json()), response.status_code

# ============================================================================
# COMMITS
# ============================================================================

@app.route("/repos/<owner>/<repo>/commits", methods=["GET"])
def list_commits(owner, repo):
    """
    List commits in a repository.
    
    Query params:
        - sha: SHA or branch to start listing commits from
        - path: only commits containing this file path
        - author: GitHub username or email
        - since: ISO 8601 timestamp
        - until: ISO 8601 timestamp
        - per_page: results per page (default: 30)
        - page: page number (default: 1)
    """
    params = {}
    for key in ["sha", "path", "author", "since", "until"]:
        if request.args.get(key):
            params[key] = request.args.get(key)
    
    params["per_page"] = request.args.get("per_page", 30)
    params["page"] = request.args.get("page", 1)
    
    response = github_request("GET", f"/repos/{owner}/{repo}/commits", params=params)
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/commits/<ref>", methods=["GET"])
def get_commit(owner, repo, ref):
    """
    Get a specific commit.
    
    Args:
        ref: Commit SHA, branch name, or tag name
    """
    response = github_request("GET", f"/repos/{owner}/{repo}/commits/{ref}")
    return jsonify(response.json()), response.status_code

# ============================================================================
# COMMENTS (PR Comments - appear in the conversation)
# ============================================================================

@app.route("/repos/<owner>/<repo>/issues/<int:issue_number>/comments", methods=["GET"])
def list_issue_comments(owner, repo, issue_number):
    """
    List comments on an issue or pull request.
    Works for both issues and PRs (PRs are treated as issues).
    """
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        params=params
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/issues/<int:issue_number>/comments", methods=["POST"])
@require_token
def create_issue_comment(owner, repo, issue_number):
    """
    Create a comment on an issue or pull request.
    
    Request body:
        - body: The comment text (required)
    """
    data = request.get_json()
    if not data or not data.get("body"):
        return jsonify({"error": "Comment body is required"}), 400
    
    response = github_request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        json={"body": data["body"]}
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/issues/comments/<int:comment_id>", methods=["PATCH"])
@require_token
def update_issue_comment(owner, repo, comment_id):
    """
    Update an issue/PR comment.
    
    Request body:
        - body: The new comment text (required)
    """
    data = request.get_json()
    if not data or not data.get("body"):
        return jsonify({"error": "Comment body is required"}), 400
    
    response = github_request(
        "PATCH",
        f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
        json={"body": data["body"]}
    )
    return jsonify(response.json()), response.status_code

# ============================================================================
# PR REVIEWS (Approve, Request Changes, Comment)
# ============================================================================

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/reviews", methods=["GET"])
def list_reviews(owner, repo, pull_number):
    """List reviews on a pull request."""
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        params=params
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/reviews/<int:review_id>", methods=["GET"])
def get_review(owner, repo, pull_number, review_id):
    """Get a specific review."""
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}"
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/reviews", methods=["POST"])
@require_token
def create_review(owner, repo, pull_number):
    """
    Create a review on a pull request.
    
    Request body:
        - body: Review comment text (optional)
        - event: APPROVE, REQUEST_CHANGES, or COMMENT (required)
        - comments: Array of inline review comments (optional)
            Each comment: {path, position or line, body, side?, start_line?, start_side?}
    """
    data = request.get_json()
    if not data or not data.get("event"):
        return jsonify({
            "error": "Event is required",
            "valid_events": ["APPROVE", "REQUEST_CHANGES", "COMMENT"]
        }), 400
    
    payload = {"event": data["event"]}
    if data.get("body"):
        payload["body"] = data["body"]
    if data.get("comments"):
        payload["comments"] = data["comments"]
    
    response = github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json=payload
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/reviews/<int:review_id>", methods=["PUT"])
@require_token
def update_review(owner, repo, pull_number, review_id):
    """
    Update a review (only the body can be updated).
    
    Request body:
        - body: The new review body text (required)
    """
    data = request.get_json()
    if not data or not data.get("body"):
        return jsonify({"error": "Review body is required"}), 400
    
    response = github_request(
        "PUT",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}",
        json={"body": data["body"]}
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/reviews/<int:review_id>/dismiss", methods=["PUT"])
@require_token
def dismiss_review(owner, repo, pull_number, review_id):
    """
    Dismiss a review.
    
    Request body:
        - message: Reason for dismissal (required)
    """
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Dismissal message is required"}), 400
    
    response = github_request(
        "PUT",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals",
        json={"message": data["message"]}
    )
    return jsonify(response.json()), response.status_code

# ============================================================================
# PR REVIEW COMMENTS (Comments on specific lines of code)
# ============================================================================

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/comments", methods=["GET"])
def list_review_comments(owner, repo, pull_number):
    """
    List review comments on a pull request.
    These are comments on specific lines of code.
    """
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/comments",
        params=params
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/comments", methods=["POST"])
@require_token
def create_review_comment(owner, repo, pull_number):
    """
    Create an inline review comment on a pull request.
    
    Request body:
        - body: The comment text (required)
        - commit_id: SHA of the commit to comment on (required)
        - path: Relative path of the file to comment on (required)
        - line: Line number in the diff to comment on (required for single line)
        - side: LEFT or RIGHT (default: RIGHT)
        - start_line: For multi-line comments, the first line
        - start_side: LEFT or RIGHT for start_line
    """
    data = request.get_json()
    required_fields = ["body", "commit_id", "path"]
    
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
    
    if not data.get("line") and not data.get("position"):
        return jsonify({"error": "Either 'line' or 'position' is required"}), 400
    
    payload = {
        "body": data["body"],
        "commit_id": data["commit_id"],
        "path": data["path"]
    }
    
    # Add optional fields
    for field in ["line", "side", "start_line", "start_side", "position"]:
        if data.get(field):
            payload[field] = data[field]
    
    response = github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/comments",
        json=payload
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/comments/<int:comment_id>", methods=["PATCH"])
@require_token
def update_review_comment(owner, repo, comment_id):
    """
    Update an inline review comment.
    
    Request body:
        - body: The new comment text (required)
    """
    data = request.get_json()
    if not data or not data.get("body"):
        return jsonify({"error": "Comment body is required"}), 400
    
    response = github_request(
        "PATCH",
        f"/repos/{owner}/{repo}/pulls/comments/{comment_id}",
        json={"body": data["body"]}
    )
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/pulls/comments/<int:comment_id>/replies", methods=["POST"])
@require_token
def reply_to_review_comment(owner, repo, comment_id):
    """
    Reply to an inline review comment.
    
    Request body:
        - body: The reply text (required)
    """
    data = request.get_json()
    if not data or not data.get("body"):
        return jsonify({"error": "Reply body is required"}), 400
    
    # Get the original comment to find the pull request number
    comment_response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    )
    
    if comment_response.status_code != 200:
        return jsonify(comment_response.json()), comment_response.status_code
    
    comment_data = comment_response.json()
    # Extract pull number from the pull_request_url
    pull_request_url = comment_data.get("pull_request_url", "")
    pull_number = pull_request_url.split("/")[-1]
    
    response = github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies",
        json={"body": data["body"]}
    )
    return jsonify(response.json()), response.status_code

# ============================================================================
# FILE CONTENTS (Useful for reviewing specific files)
# ============================================================================

@app.route("/repos/<owner>/<repo>/contents/<path:file_path>", methods=["GET"])
def get_file_contents(owner, repo, file_path):
    """
    Get contents of a file in the repository.
    
    Query params:
        - ref: Branch, tag, or commit SHA (default: default branch)
    """
    params = {}
    if request.args.get("ref"):
        params["ref"] = request.args.get("ref")
    
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/contents/{file_path}",
        params=params
    )
    return jsonify(response.json()), response.status_code

# ============================================================================
# BRANCHES (Useful for PR context)
# ============================================================================

@app.route("/repos/<owner>/<repo>/branches", methods=["GET"])
def list_branches(owner, repo):
    """List branches in a repository."""
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request("GET", f"/repos/{owner}/{repo}/branches", params=params)
    return jsonify(response.json()), response.status_code

@app.route("/repos/<owner>/<repo>/branches/<branch>", methods=["GET"])
def get_branch(owner, repo, branch):
    """Get a specific branch."""
    response = github_request("GET", f"/repos/{owner}/{repo}/branches/{branch}")
    return jsonify(response.json()), response.status_code

# ============================================================================
# COMPARE (Useful for seeing diff between branches/commits)
# ============================================================================

@app.route("/repos/<owner>/<repo>/compare/<basehead>", methods=["GET"])
def compare_commits(owner, repo, basehead):
    """
    Compare two commits/branches/tags.
    
    Args:
        basehead: Format "base...head" (e.g., "main...feature-branch")
    
    Query params:
        - per_page: Number of files to return (default: 30)
        - page: Page number (default: 1)
    """
    params = {
        "per_page": request.args.get("per_page", 30),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/compare/{basehead}",
        params=params
    )
    return jsonify(response.json()), response.status_code

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# API DOCUMENTATION
# ============================================================================

@app.route("/", methods=["GET"])
def api_docs():
    """Return API documentation."""
    return jsonify({
        "name": "GitHub PR Review Tool API",
        "version": "1.0.0",
        "endpoints": {
            "health": {
                "GET /health": "Health check"
            },
            "repository": {
                "GET /repos/{owner}/{repo}": "Get repository info"
            },
            "pull_requests": {
                "GET /repos/{owner}/{repo}/pulls": "List pull requests",
                "GET /repos/{owner}/{repo}/pulls/{pull_number}": "Get a pull request",
                "GET /repos/{owner}/{repo}/pulls/{pull_number}/files": "Get PR files/diff",
                "GET /repos/{owner}/{repo}/pulls/{pull_number}/commits": "Get PR commits"
            },
            "commits": {
                "GET /repos/{owner}/{repo}/commits": "List commits",
                "GET /repos/{owner}/{repo}/commits/{ref}": "Get a commit"
            },
            "reviews": {
                "GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews": "List reviews",
                "GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}": "Get review",
                "POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews": "Create review (APPROVE/REQUEST_CHANGES/COMMENT)",
                "PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}": "Update review",
                "PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismiss": "Dismiss review"
            },
            "review_comments": {
                "GET /repos/{owner}/{repo}/pulls/{pull_number}/comments": "List review comments",
                "POST /repos/{owner}/{repo}/pulls/{pull_number}/comments": "Create review comment",
                "PATCH /repos/{owner}/{repo}/pulls/comments/{comment_id}": "Update review comment",
                "POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/replies": "Reply to review comment"
            },
            "files": {
                "GET /repos/{owner}/{repo}/contents/{path}": "Get file contents"
            },
            "branches": {
                "GET /repos/{owner}/{repo}/branches": "List branches",
                "GET /repos/{owner}/{repo}/branches/{branch}": "Get branch"
            },
            "compare": {
                "GET /repos/{owner}/{repo}/compare/{base}...{head}": "Compare commits/branches"
            },
            },
        "authentication": "Set GITHUB_TOKEN environment variable for write operations",
        "note": "This server proxies requests to the GitHub API"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    print(f"🚀 GitHub PR Review Tool API")
    print(f"📍 Running on http://localhost:{port}")
    print(f"🔑 GitHub Token: {'Configured' if GITHUB_TOKEN else 'Not configured'}")
    print(f"📚 API Docs: http://localhost:{port}/")
    
    app.run(host="0.0.0.0", port=port, debug=debug)

