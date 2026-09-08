# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///

# %%

from __future__ import annotations

import asyncio

from unique_toolkit.experimental.components.content_tree import ContentTree


async def main() -> None:
    tree_svc = ContentTree.from_settings()

    print("=== Visible KB tree (unlimited depth) ===")
    print(await tree_svc.render_visible_tree_via_folders_async(max_depth=None))

    print("=== Same view, max depth 2 (fetch stops at depth 2) ===")
    print(await tree_svc.render_visible_tree_via_folders_async(max_depth=2))


if __name__ == "__main__":
    asyncio.run(main())
