import asyncio

from fastmcp import Client


async def main():
    async with Client("<YOUR_MCP_SERVER_URL>/mcp", auth="oauth"):
        print("✓ Authenticated!")


if __name__ == "__main__":
    asyncio.run(main())
