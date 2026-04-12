"""
GitHub PR Review Tool - HTTP Server
Exposes only: get pull request files, add comment (for code review agent).
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
    response = requests.request(method, url, headers=get_headers(), **kwargs)
    return response


def require_token(f):
    """Decorator to require GitHub token for write operations."""
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
# GET PULL REQUEST (files/diff for code review)
# ============================================================================

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/files", methods=["GET"])
def get_pull_request_files(owner, repo, pull_number):
    """Get files changed in a pull request (diffs and stats)."""
    params = {
        "per_page": request.args.get("per_page", 50),
        "page": request.args.get("page", 1)
    }
    response = github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
        params=params
    )
    return jsonify(response.json()), response.status_code


# ============================================================================
# ADD PR REVIEW COMMENT (submits a review on the PR)
# ============================================================================

@app.route("/repos/<owner>/<repo>/pulls/<int:pull_number>/reviews", methods=["POST"])
@require_token
def create_pr_review(owner, repo, pull_number):
    """
    Create a review on a pull request (PR comment).
    Body: {"event": "COMMENT" | "APPROVE" | "REQUEST_CHANGES", "body": "your comment text"}
    Use event "COMMENT" to add a review comment without approving or requesting changes.
    """
    data = request.get_json()
    if not data or not data.get("event"):
        return jsonify({
            "error": "event is required",
            "valid_events": ["APPROVE", "REQUEST_CHANGES", "COMMENT"]
        }), 400

    payload = {"event": data["event"]}
    if data.get("body"):
        payload["body"] = data["body"]

    response = github_request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json=payload
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
        "name": "GitHub PR Review Tool API (code review agent)",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "get_pull_request_files": "GET /repos/{owner}/{repo}/pulls/{pull_number}/files",
            "create_pr_review": "POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews (body: { \"event\": \"COMMENT\", \"body\": \"...\" })",
        },
        "authentication": "Set GITHUB_TOKEN for write endpoints",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    print(f"GitHub PR Review API (get PR files + add comment)")
    print(f"Running on http://localhost:{port}")
    print(f"GitHub Token: {'Configured' if GITHUB_TOKEN else 'Not configured'}")
    app.run(host="0.0.0.0", port=port, debug=debug)
