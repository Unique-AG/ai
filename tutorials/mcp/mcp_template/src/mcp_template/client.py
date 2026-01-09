"""
Example MCP client code demonstrating how to connect to and interact with the MCP server.
"""

import asyncio
import json

from fastmcp import Client


async def main():
    """
    Example client that connects to the MCP server and lists available tools.
    """
    async with Client("http://localhost:8003/mcp", auth="oauth") as client:
        print("✓ Authenticated!")
        tools = await client.list_tools()

        print(f"\nFound {len(tools)} tools:\n")
        for tool in tools:
            print(f"TOOL: {tool.name}")
            print(f"DESCRIPTION: {tool.description}")
            print(f"SCHEMA: {json.dumps(tool.model_dump(), indent=2)}")
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
