# %%
from __future__ import annotations

import asyncio

from unique_toolkit.experimental.content_tree import ContentTree


async def main() -> None:
    tree_svc = ContentTree.from_settings()

    print("=== Visible KB tree (unlimited depth) ===")
    print(await tree_svc.render_visible_tree_async(max_depth=None))

    print("=== Same view, max depth 2 (tree -L 2 style) ===")
    print(await tree_svc.render_visible_tree_async(max_depth=2))


if __name__ == "__main__":
    asyncio.run(main())
