# Content tree (experimental)

!!! warning "Experimental"

    :class:`~unique_toolkit.experimental.components.content_tree.service.ContentTree` lives
    under :mod:`unique_toolkit.experimental` and is **not** wired into
    :class:`~unique_toolkit.services.factory.UniqueServiceFactory`. The API may
    change between minor releases — import it explicitly from its experimental
    subpackage and pin your toolkit version if you depend on its current shape.

The :class:`~unique_toolkit.experimental.components.content_tree.service.ContentTree` builds a **filesystem-style tree** of knowledge-base folders and files the acting user can see.

**Folder-walk methods** (`resolve_visible_file_paths_via_folders_async`, `render_visible_tree_via_folders_async`) return a :class:`~unique_toolkit.experimental.components.content_tree.schemas.FolderWalkSnapshot`. A **depth limit** actually reduces backend work (like ``tree -L``), empty folders appear, and an optional **timeout** can return a partial tree while the walk continues to fill the cache.

**Deprecated methods** (`resolve_visible_file_paths_async`, `render_visible_tree_async`) keep the original signatures and still work; they call the folder-walk methods.

Rendering follows **GNU/Linux ``tree(1)``** conventions: sorted directories and files, UTF-8 box-drawing characters.

!!! note "Environment"

    Use the same SDK / :class:`~unique_toolkit.app.unique_settings.UniqueSettings` setup as other toolkit examples (`UNIQUE_API_KEY`, `UNIQUE_APP_ID`, user and company context). The sample script uses :meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.from_settings`.

## What you get

1. **Walk folders** the user can list through ``Folder.get_infos`` (names included; empty directories included).
2. **List files** in each visited directory through ``Content.get_infos(parentId)``.
3. **Print** a multi-line tree string via :meth:`~unique_toolkit.experimental.components.content_tree.schemas.FolderWalkSnapshot.render` (or ``str(snapshot)``). Pass ``show_files=False`` for directories only (``tree -d``).

## Full tree, depth limit, and timeout

Use :meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.render_visible_tree_via_folders_async`. Pass ``max_depth=None`` for an unlimited walk, or an integer so **only that many directory levels are fetched**. ``timeout`` (seconds) returns a partial tree if the walk is still running; a later call without ``timeout`` reuses the same cached walk.

```{.python #kb-tree-imports}
from __future__ import annotations

import asyncio

from unique_toolkit.experimental.components.content_tree import ContentTree
```

```{.python #kb-tree-async-main}
async def main() -> None:
    tree_svc = ContentTree.from_settings()

    print("=== Visible KB tree (unlimited depth) ===")
    print(await tree_svc.render_visible_tree_via_folders_async(max_depth=None))

    print("=== Same view, max depth 2 (fetch stops at depth 2) ===")
    print(await tree_svc.render_visible_tree_via_folders_async(max_depth=2))


if __name__ == "__main__":
    asyncio.run(main())
```

### Runnable script

```{.python #kb-tree-main file=docs/.python_files/kb_tree_visible.py}
<<example-script-deps>>

<<kb-tree-imports>>

<<kb-tree-async-main>>
```

??? example "Full example (click to expand)"

    <!--codeinclude-->
    [Content tree (visible content)](../../../examples_from_docs/kb_tree_visible.py)
    <!--/codeinclude-->

## Listing, filter, and search

:meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.list_visible_files_async`,
:meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.filter_visible_files_async`,
and :meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.search_visible_files_fuzzy_async`
share the folder-walk snapshot from
:meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.resolve_visible_file_paths_via_folders_async`.
The deprecated :meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.resolve_visible_file_paths_async`
still returns ``(content_info, path_segments)`` rows (``list[str]``). For timeout slices
or ``tree -d``, use the via-folders snapshot and
:meth:`~unique_toolkit.experimental.components.content_tree.schemas.FolderWalkSnapshot.render`.

```python
files = await tree_svc.list_visible_files_async()
hits = await tree_svc.search_visible_files_fuzzy_async("contract_2024", limit=5)
rows = await tree_svc.resolve_visible_file_paths_async()
snapshot = await tree_svc.resolve_visible_file_paths_via_folders_async(
    max_depth=2, timeout=5.0
)
print(snapshot.render(show_files=False))
```

## Optional metadata filter

``metadata_filter`` is forwarded to per-folder content listings (same idea as smart rules / filters in the [Knowledge Base service](../content/kb_service.md) and [Smart Rules](../content/smart_rules.md)). Example shape:

```{.python #kb-tree-filter-snippet}
# Example only — adjust to your metadata / smart-rule JSON.
await tree_svc.render_visible_tree_via_folders_async(
    metadata_filter={"department": "legal"},
    max_depth=3,
)
```

## Related

- [Content folder service](../content/content-folder.md) — create/delete **folders** (scopes) and ACL.
- [Knowledge Base service examples](../content/kb_service.md) — upload, search, and filter **content**.
