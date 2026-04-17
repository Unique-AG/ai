# ~/~ begin <<docs/modules/examples/content/content-tree.md#kb-tree-main>>[init]
# ~/~ begin <<docs/modules/examples/content/content-tree.md#kb-tree-imports>>[init]
from __future__ import annotations

import asyncio

from unique_toolkit.content.tree import ContentTree
# ~/~ end


# ~/~ begin <<docs/modules/examples/content/content-tree.md#kb-tree-async-main>>[init]
async def main() -> None:
    tree_svc = ContentTree.from_settings()

    print("=== Visible KB tree (unlimited depth) ===")
    print(await tree_svc.render_visible_tree_async(max_depth=None))

    print("=== Same view, max depth 2 (tree -L 2 style) ===")
    print(await tree_svc.render_visible_tree_async(max_depth=2))


if __name__ == "__main__":
    asyncio.run(main())
# ~/~ end
# ~/~ end
