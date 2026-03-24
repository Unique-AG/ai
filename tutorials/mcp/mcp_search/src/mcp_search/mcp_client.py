import asyncio
import os

from fastmcp import Client

MCP_URL = os.environ.get("MCP_SEARCH_URL", "http://localhost:8003/mcp")

SEARCH_ARGS = {
    "search_string": "what is unique?",
    "search_type": "VECTOR",
    "limit": 3,
}


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

        # --- Call 1: normal auth (JWT claims / userinfo) ---
        print("\n--- Call 1: auth from JWT / userinfo ---")
        result = await client.call_tool("search", SEARCH_ARGS)
        print(f"Got {len(result.content)} result(s):")
        _print_result(result)

        # --- Call 2: override auth via _meta ---
        meta_user = os.environ.get("UNIQUE_AUTH_USER_ID", "meta-test-user")
        meta_company = os.environ.get("UNIQUE_AUTH_COMPANY_ID", "meta-test-company")
        meta_override = {
            "unique.app/user-id": meta_user,
            "unique.app/company-id": meta_company,
        }
        print(f"\n--- Call 2: auth from _meta {meta_override} ---")
        result = await client.call_tool("search", SEARCH_ARGS, meta=meta_override)
        print(f"Got {len(result.content)} result(s):")
        _print_result(result)


if __name__ == "__main__":
    asyncio.run(main())
