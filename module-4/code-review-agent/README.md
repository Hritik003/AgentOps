# Module 4: Code Agent

A generic **agentic** assistant that can use any MCP tools (GitHub, Jira, etc.) to accomplish tasks described in natural language.

- **MCP tools** — GitHub (PRs, branches, file ops), Jira (issues, search), and more
- An **OpenAI-compliant** inference endpoint for the LLM
- **Interactive chat** — the agent loops until the task is done, calling as many tools as needed

## Prerequisites

- Python 3.10+
- Completed Modules 1–3
- API credentials (provided during workshop)

## Environment variables

Create a `.env` file with your credentials:

```env
OPENAI_BASE_URL=<your-api-endpoint>
OPENAI_API_KEY=<your-api-key>
MCP_SERVER_URL=<your-mcp-server-url>
MCP_AUTH_TOKEN=<your-mcp-auth-token>
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_BASE_URL` | Yes | Base URL of your OpenAI-compliant API. |
| `OPENAI_API_KEY` | Yes | API key for the inference endpoint. |
| `MCP_SERVER_URL` | Yes | MCP server URL. |
| `MCP_AUTH_TOKEN` | Yes | Bearer token for MCP auth. |
| `OPENAI_MODEL` | No | Model name (default: `gptoss120b--ep-klmd`). |

## Setup

```bash
cd module-4/code-review-agent
pip install -r requirements.txt
```

## Run

### Interactive mode (default)

```bash
python agent.py
```

This starts an interactive chat — type any task and the agent will break it down, call tools, and complete it. Type `exit` to quit.

### Single query mode

```bash
python agent.py "Analyze Jira issue NAI-4199 and raise a PR to fix it in Hritik003/test-repo"
```

### From the notebook

Open `code-review-agent.ipynb`, run all cells, and type your query in the input prompt.

## Project structure

```
code-review-agent/
├── agent.py                   # MCP client + generic agent loop + interactive CLI
├── code-review-agent.ipynb    # Same flow in a Jupyter notebook
├── requirements.txt
├── .env                       # Your credentials (not committed)
└── README.md
```
