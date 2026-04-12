#!/usr/bin/env python3
"""
Simple MCP client using the official MCP Python SDK (Streamable HTTP transport).
Works with any Streamable HTTP MCP server, including:

  - mcp-proxy:  python server.py  (default http://localhost:8080/mcp)
  - using-mcp-sdk server_http:  python server_http.py  (default http://localhost:8000/mcp)

Usage:
  pip install -r requirements.txt
  python client_demo.py [URL]

  Default URL: MCP_SERVER_URL env, or http://localhost:8080/mcp
  Examples:
    python client_demo.py
    python client_demo.py http://localhost:8000/mcp   # SDK server
    python client_demo.py http://localhost:8080/mcp   # proxy server
"""

import asyncio
import json
import os
import sys


async def run(url: str) -> None:
    try:
        import anyio
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except ImportError as e:
        print("Install the MCP SDK:  pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1) from e

    print(f"Connecting to {url} ...")
    async with streamable_http_client(url, terminate_on_close=False) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize
            init_result = await session.initialize()
            print("Initialize:", json.dumps(init_result.model_dump(), indent=2, default=str))

            # List tools
            tools_result = await session.list_tools()
            print("\nTools:")
            for t in tools_result.tools:
                print(f"  - {t.name}: {t.description or '(no description)'}")

            # Call get_pull_request_files
            print("\nCalling get_pull_request_files(owner='octocat', repo='hello-world', pull_number=1) ...")
            call_result = await session.call_tool(
                "get_pull_request_files",
                arguments={"owner": "octocat", "repo": "hello-world", "pull_number": 1},
            )
            if getattr(call_result, "is_error", False):
                print("Tool error:", call_result.content)
            else:
                for block in call_result.content:
                    if hasattr(block, "text") and block.text:
                        print(block.text[:500] + ("..." if len(block.text) > 500 else ""))

    print("\nDone.")


def main() -> None:
    url = os.environ.get("MCP_SERVER_URL", os.environ.get("MCP_PROXY_URL", "http://localhost:8080/mcp"))
    if len(sys.argv) > 1:
        url = sys.argv[1]
    try:
        import anyio
        anyio.run(run, url, backend="asyncio")
    except ImportError:
        asyncio.run(run(url))


if __name__ == "__main__":
    main()
