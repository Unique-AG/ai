import asyncio

from fastmcp import Client


async def main():
    async with Client("http://localhost:8003/mcp", auth="oauth") as client:
        print("✓ Authenticated!")
        print(await client.list_tools())

        print(await client.call_tool("addition", arguments={"a": 1, "b": 2}))
        print(
            await client.call_tool(
                "search",
                arguments={
                    "search_string": "Harry Potter",
                    "search_type": "COMBINED",
                    "limit": 10,
                },
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
