"""Experimental content-tree subpackage: visible-content listing, tree rendering, and fuzzy search.

!!! warning "Experimental"
    This subpackage lives under :mod:`unique_toolkit.experimental` and is not
    wired into :class:`~unique_toolkit.services.factory.UniqueServiceFactory`.
    Its API may change between minor releases.

Typical usage::

    from unique_toolkit.experimental.components.content_tree import ContentTree

    tree = ContentTree.from_settings()
    print(await tree.render_visible_tree_async(max_depth=2))
    hits = await tree.search_visible_files_fuzzy_async("annual_report")

The subpackage is split into three modules to mirror the rest of the
``content`` domain:

- :mod:`unique_toolkit.experimental.components.content_tree.schemas` — data classes
  (:class:`PathTrieNode`, :class:`FuzzyMatch`, :data:`MatchTarget`).
- :mod:`unique_toolkit.experimental.components.content_tree.functions` — pure helpers
  for listing, scope-id resolution, trie construction, and ``tree(1)``-style
  formatting.
- :mod:`unique_toolkit.experimental.components.content_tree.service` —
  :class:`ContentTree`, the orchestrating service with per-instance caching.
"""

from unique_toolkit.experimental.components.content_tree.functions import (
    build_trie_from_resolved_paths,
    extract_scope_ids_from_content_infos,
    format_path_trie,
    get_all_content_infos_async,
    resolve_visible_file_paths_core,
    translate_scope_id_async,
    translate_scope_ids_async,
    translate_scope_ids_batch,
)
from unique_toolkit.experimental.components.content_tree.schemas import (
    FuzzyMatch,
    MatchTarget,
    PathTrieNode,
)
from unique_toolkit.experimental.components.content_tree.service import ContentTree

__all__ = [
    "ContentTree",
    "FuzzyMatch",
    "MatchTarget",
    "PathTrieNode",
    "build_trie_from_resolved_paths",
    "extract_scope_ids_from_content_infos",
    "format_path_trie",
    "get_all_content_infos_async",
    "resolve_visible_file_paths_core",
    "translate_scope_id_async",
    "translate_scope_ids_async",
    "translate_scope_ids_batch",
]
