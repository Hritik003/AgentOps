# Code Review Agent (Demo)

Minimal **agentic** app that reviews a pull request and posts a comment using:

- **2 MCP tools** from [code-review-mcp-server](../code-review-mcp-server):  
  `get_pull_request_files`, `create_issue_comment`
- An **OpenAI-compliant** inference endpoint for the LLM

Flow: **Get PR files** → **LLM generates review** → **Post comment on PR**.

## Prerequisites

1. **Code review backend and MCP proxy** must be running:
   - [code-review-server](../code-review-server): Flask app that talks to GitHub (default `http://localhost:5000`)
   - [code-review-mcp-server/mcp-proxy](../code-review-mcp-server/mcp-proxy): MCP over HTTP (default `http://localhost:8080`)
2. **GitHub token** for posting comments: set `GITHUB_TOKEN` where the code-review-server runs.
3. **OpenAI-compliant endpoint**: any API that supports Chat Completions with tool/function calling (e.g. OpenAI, Azure OpenAI, or a custom inference endpoint).

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_BASE` | Yes | Base URL of your OpenAI-compliant API (e.g. `https://api.openai.com/v1` or your inference endpoint). |
| `OPENAI_API_KEY` | Yes | API key for that endpoint. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o`). |
| `MCP_PROXY_URL` | No | MCP proxy base URL (default: `http://localhost:8080`). |
| `MCP_PROXY_BEARER_TOKEN` | No | Bearer token for MCP proxy auth; if set, sent as `Authorization: Bearer <token>`. |

## Setup

```bash
cd module-4/code-review-agent
pip install -r requirements.txt
```

## Run

```bash
export OPENAI_API_BASE="https://your-inference-endpoint/v1"
export OPENAI_API_KEY="your-api-key"

python agent.py <owner> <repo> <pull_number>
```

Example:

```bash
python agent.py octocat hello-world 123
```

The agent will:

1. Call **get_pull_request_files** (via MCP) to fetch the PR diff.
2. Send the diff to your inference endpoint to generate a review.
3. Call **create_issue_comment** (via MCP) to post the review as a PR comment.

## Project structure

```
code-review-agent/
├── agent.py               # MCP client + agent loop + CLI
├── code_review_agent.ipynb # Same flow in a Jupyter notebook
├── requirements.txt
└── README.md
```

To run from a notebook: open `code_review_agent.ipynb`, set config (cell 1) and `owner` / `repo` / `pull_number` (cell 5), then run all cells.

## MCP tools used

- **get_pull_request_files** – Get changed files and patches for the PR (read).
- **create_issue_comment** – Create a comment on the PR (write; requires `GITHUB_TOKEN` on the code-review-server).
