import asyncio

from fastmcp import Client

SERVERS = {
    "Hello Server": "http://localhost:5032/hello/mcp",
    "Goodbye Server": "http://localhost:5032/goodbye/mcp",
}


async def test_server(name: str, url: str):
    print(f"\n{'='*50}")
    print(f"Connecting to: {name} ({url})")
    print("=" * 50)

    async with Client(url) as client:
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")

        for tool in tools:
            result = await client.call_tool(tool.name, {"name": "World"})
            print(f"  {tool.name}('World') => {result.data}")


async def main():
    for name, url in SERVERS.items():
        await test_server(name, url)


if __name__ == "__main__":
    asyncio.run(main())
