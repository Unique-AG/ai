# Content tree (experimental)

!!! warning "Experimental"

    :class:`~unique_toolkit.experimental.content_tree.service.ContentTree` lives
    under :mod:`unique_toolkit.experimental` and is **not** wired into
    :class:`~unique_toolkit.services.factory.UniqueServiceFactory`. The API may
    change between minor releases — import it explicitly from its experimental
    subpackage and pin your toolkit version if you depend on its current shape.

The :class:`~unique_toolkit.experimental.content_tree.service.ContentTree` builds a **filesystem-style tree** of knowledge-base **content the acting user can see**. It is **not** the full folder hierarchy from :class:`~unique_toolkit.content.folder.service.ContentFolder`—only folders that appear on visible content paths (via ``folderIdPath`` metadata) show up.

Rendering follows **GNU/Linux ``tree(1)``** conventions: sorted directories and files, UTF-8 box-drawing characters, and an optional **depth limit** (like ``tree -L``).

Beyond rendering, the same loaded snapshot powers **flat listing**, **client-side filtering**, and **fuzzy file search** — all reading from the per-instance cache so extra queries don't re-hit the backend.

!!! note "Environment"

    Use the same SDK / :class:`~unique_toolkit.app.unique_settings.UniqueSettings` setup as other toolkit examples (`UNIQUE_API_KEY`, `UNIQUE_APP_ID`, user and company context). The sample script uses :meth:`~unique_toolkit.experimental.content_tree.service.ContentTree.from_settings`.

## What you get

1. **List content** visible to the user through the underlying :class:`~unique_toolkit.services.knowledge_base.KnowledgeBaseService`.
2. **Resolve** each item’s ``folderIdPath`` segments to **folder names** (batched scope-id lookups).
3. **Build a trie** and **print** a multi-line tree string — or walk the flat snapshot for listing, filtering, and fuzzy search.

Content without a ``folderIdPath`` is grouped under a synthetic ``_no_folder_path`` segment (same behaviour as the legacy path logic in the tree module).

## Full tree and depth limit

Use :meth:`~unique_toolkit.experimental.content_tree.service.ContentTree.render_visible_tree_async`. Pass ``max_depth=None`` for an unlimited tree, or an integer for **``tree -L``-style** truncation: depth ``1`` shows only top-level folders and files; deeper levels are summarized as a single “…” line with counts when cut off.

```{.python #kb-tree-imports}
from __future__ import annotations

import asyncio

from unique_toolkit.experimental.content_tree import ContentTree
```

```{.python #kb-tree-async-main}
async def main() -> None:
    tree_svc = ContentTree.from_settings()

    print("=== Visible KB tree (unlimited depth) ===")
    print(await tree_svc.render_visible_tree_async(max_depth=None))

    print("=== Same view, max depth 2 (tree -L 2 style) ===")
    print(await tree_svc.render_visible_tree_async(max_depth=2))


if __name__ == "__main__":
    asyncio.run(main())
```

### Runnable script

```{.python #kb-tree-main file=docs/.python_files/kb_tree_visible.py}
<<kb-tree-imports>>

<<kb-tree-async-main>>
```

??? example "Full example (click to expand)"

    <!--codeinclude-->
    [Content tree (visible content)](../../../examples_from_docs/kb_tree_visible.py)
    <!--/codeinclude-->

## Flat listing and filtering

If you want the raw list of visible files (not a tree), use :meth:`~unique_toolkit.experimental.content_tree.service.ContentTree.list_visible_files_async`. For predicates the server-side ``metadata_filter`` can't express — arbitrary Python over :class:`~unique_toolkit.content.schemas.ContentInfo` — use :meth:`~unique_toolkit.experimental.content_tree.service.ContentTree.filter_visible_files_async`:

```python
# Every visible file, flat
files = await tree_svc.list_visible_files_async()

# Client-side filter over the cached snapshot
pdfs = await tree_svc.filter_visible_files_async(
    lambda info: info.mime_type == "application/pdf"
)
```

Both calls share the same cached snapshot as ``render_visible_tree_async``, so the first one pays the fetch and the rest are free.

## Fuzzy file search

:meth:`~unique_toolkit.experimental.content_tree.service.ContentTree.search_visible_files_fuzzy_async` matches a query against the file basename, the joined folder path, or both. Scoring uses stdlib :class:`difflib.SequenceMatcher`; matching is **case-insensitive by default**. Results come back as :class:`~unique_toolkit.experimental.content_tree.schemas.FuzzyMatch` records sorted by descending score:

```python
hits = await tree_svc.search_visible_files_fuzzy_async(
    "contract_2024",
    limit=5,
    min_score=0.6,
    match_on="both",   # "key" | "path" | "both"
)

for hit in hits:
    print(f"{hit.score:.2f}  {'/'.join(hit.path_segments)}  (via {hit.matched_on})")
```

## Optional metadata filter

``metadata_filter`` is forwarded to content listing (same idea as smart rules / filters in the [Knowledge Base service](../content/kb_service.md) and [Smart Rules](../content/smart_rules.md)). Example shape:

```{.python #kb-tree-filter-snippet}
# Example only — adjust to your metadata / smart-rule JSON.
await tree_svc.render_visible_tree_async(
    metadata_filter={"department": "legal"},
    max_depth=3,
)
```

## Related

- [Content folder service](../content/content-folder.md) — create/delete **folders** (scopes) and ACL.
- [Knowledge Base service examples](../content/kb_service.md) — upload, search, and filter **content**.
