import asyncio
import os

from fastmcp import Client

MCP_URL = os.environ.get("MCP_SEARCH_URL", "http://localhost:8003/mcp")


async def main() -> None:
    async with Client(MCP_URL, auth="oauth") as client:
        print("✓ Authenticated!")

        tools = await client.list_tools()
        print(f"\nAvailable tools: {[t.name for t in tools]}")

        print("\n--- Calling search tool ---")
        result = await client.call_tool(
            "search",
            {
                "search_string": "what is unique?",
                "search_type": "VECTOR",
                "limit": 3,
            },
        )

        print(f"Got {len(result.content)} result(s):\n")
        for i, item in enumerate(result.content, 1):
            raw = getattr(item, "text", str(item))
            preview = raw[:200] if isinstance(raw, str) else str(raw)[:200]
            print(f"[{i}] {preview}")


if __name__ == "__main__":
    asyncio.run(main())
