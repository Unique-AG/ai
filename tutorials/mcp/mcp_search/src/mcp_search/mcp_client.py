import asyncio
import json

from fastmcp import Client


async def main():
    async with Client("http://localhost:8003/mcp", auth="oauth") as client:
        print("✓ Authenticated!")
        tools = await client.list_tools()

        for tool in tools:
            print("TOOL: ", tool.name)
            print("TOOL SCHEMA: ", json.dumps(tool.model_dump(), indent=4))


if __name__ == "__main__":
    asyncio.run(main())
