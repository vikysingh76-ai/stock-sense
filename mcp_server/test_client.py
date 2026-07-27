"""Small standalone smoke-test for india_stock_mcp.py.

Spawns the MCP server as a subprocess and exercises a handful of tools over
the real MCP stdio protocol. Not part of the app itself -- just a manual
sanity check.

Usage:
    python mcp_server/test_client.py
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = Path(__file__).parent / "india_stock_mcp.py"


async def main() -> None:
    """Spawn the MCP server and exercise a handful of its tools over stdio."""
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Discovered {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}")

            print("\n--- get_market_indices ---")
            result = await session.call_tool("get_market_indices", {})
            for block in result.content:
                print(getattr(block, "text", block))

            print("\n--- get_stock_quote(RELIANCE.NS) ---")
            result = await session.call_tool("get_stock_quote", {"ticker": "RELIANCE.NS"})
            for block in result.content:
                print(getattr(block, "text", block))

            print("\n--- update_watchlist(add, TEST.NS) ---")
            result = await session.call_tool(
                "update_watchlist",
                {"action": "add", "ticker": "TEST.NS", "name": "Test Co", "notes": "smoke test"},
            )
            for block in result.content:
                print(getattr(block, "text", block))

            print("\n--- get_watchlist ---")
            result = await session.call_tool("get_watchlist", {})
            for block in result.content:
                print(getattr(block, "text", block))

            print("\n--- update_watchlist(remove, TEST.NS) ---")
            result = await session.call_tool(
                "update_watchlist", {"action": "remove", "ticker": "TEST.NS"}
            )
            for block in result.content:
                print(getattr(block, "text", block))


if __name__ == "__main__":
    asyncio.run(main())
