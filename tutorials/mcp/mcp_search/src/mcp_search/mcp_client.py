import asyncio
import os

from fastmcp import Client

from mcp_search.config import SearchToolConfig
from unique_mcp.meta.keys import CONFIG_META_KEY, MetaKeys

MCP_URL = os.environ.get("MCP_SEARCH_URL", "http://localhost:8003/mcp")

# Only search_string is a tool argument; everything else lives in config.
SEARCH_ARGS = {"search_string": "what is unique?"}

# Optional: override config injected by the host (useful for local testing).
_CONFIG_OVERRIDE = SearchToolConfig().model_dump(mode="json", by_alias=True)


def _print_result(result: object) -> None:
    for i, item in enumerate(result.content, 1):  # type: ignore[attr-defined]
        raw = getattr(item, "text", str(item))
        preview = raw[:200] if isinstance(raw, str) else str(raw)[:200]
        print(f"  [{i}] {preview}")


async def main() -> None:
    async with Client(MCP_URL, auth="oauth") as client:
        print("✓ Authenticated!")

        tools = await client.list_tools()
        print(f"\nAvailable tools: {[t.name for t in tools]}")

        # --- Call 1: normal auth (JWT claims / userinfo), default server config ---
        print("\n--- Call 1: auth from JWT / userinfo ---")
        result = await client.call_tool(
            "search",
            SEARCH_ARGS,
            meta={"debug.probe": "mcp_client_call1"},
        )
        print(f"Got {len(result.content)} result(s):")
        _print_result(result)

        # --- Call 2: override auth + config via _meta ---
        meta_override = {
            MetaKeys.USER_ID.value: os.environ.get(
                "UNIQUE_AUTH_USER_ID", "meta-test-user"
            ),
            MetaKeys.COMPANY_ID.value: os.environ.get(
                "UNIQUE_AUTH_COMPANY_ID", "meta-test-company"
            ),
            CONFIG_META_KEY: _CONFIG_OVERRIDE,
        }
        print("\n--- Call 2: auth + config from _meta ---")
        result = await client.call_tool("search", SEARCH_ARGS, meta=meta_override)
        print(f"Got {len(result.content)} result(s):")
        _print_result(result)


if __name__ == "__main__":
    asyncio.run(main())
