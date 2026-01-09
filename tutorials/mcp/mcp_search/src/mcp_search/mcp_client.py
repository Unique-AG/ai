import asyncio
import json

from fastmcp import Client

from unique_mcp.settings import ServerSettings

server_settings = ServerSettings()  # type: ignore

print("MCP URL: ", server_settings.base_url.encoded_string())


async def main():
    async with Client(
        server_settings.base_url.encoded_string() + "mcp/", auth="oauth"
    ) as client:
        print("✓ Authenticated!")
        tools = await client.list_tools()

        for tool in tools:
            print("TOOL: ", tool.name)
            print("TOOL SCHEMA: ", json.dumps(tool.model_dump(), indent=4))

        result = await client.call_tool(
            name="search",
            arguments={
                "search_string": "What is the capital of France?",
            },
        )
        print("RESULT: ", result)


if __name__ == "__main__":
    asyncio.run(main())
