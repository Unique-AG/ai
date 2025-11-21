from fastmcp import Client
import asyncio

async def main():
    async with Client("<YOUR_MCP_SERVER_URL>/mcp", auth="oauth") as client:

        print("✓ Authenticated!")
        
if __name__ == "__main__":
    asyncio.run(main())