"""Experimental content-tree subpackage: visible-content listing, tree rendering, and fuzzy search.

!!! warning "Experimental"
    This subpackage lives under :mod:`unique_toolkit.experimental` and is not
    wired into :class:`~unique_toolkit.services.factory.UniqueServiceFactory`.
    Its API may change between minor releases.

Typical usage::

    from unique_toolkit.experimental.components.content_tree import ContentTree

    tree = ContentTree.from_settings()
    snapshot = await tree.resolve_visible_file_paths_via_folders_async(
        max_depth=2, timeout=5.0
    )
    print(snapshot.render(show_files=False))
    print(await tree.render_visible_tree_via_folders_async(max_depth=2))

The subpackage is split into:

- :mod:`unique_toolkit.experimental.components.content_tree.schemas` — data classes
  (:class:`PathTrieNode`, :class:`FuzzyMatch`, :class:`FolderWalkSnapshot`;
  file locations are :class:`~pathlib.PurePosixPath`).
- :mod:`unique_toolkit.experimental.components.content_tree.functions` — folder-walk
  helpers and ``tree(1)``-style formatting.
- :mod:`unique_toolkit.experimental.components.content_tree.deprecated` — legacy
  full-catalog ``ContentInfo`` listing.
- :mod:`unique_toolkit.experimental.components.content_tree.service` —
  :class:`ContentTree`, the orchestrating service with per-instance caching.
"""

from unique_toolkit.experimental.components.content_tree.deprecated import (
    extract_leaf_scope_ids_from_content_infos,
    extract_scope_ids_from_content_infos,
    get_all_content_infos_async,
    translate_folder_path_async,
    translate_folder_paths_async,
    translate_scope_id_async,
    translate_scope_ids_async,
    translate_scope_ids_batch,
)
from unique_toolkit.experimental.components.content_tree.functions import (
    build_trie_from_resolved_paths,
    format_path_trie,
    resolve_visible_file_paths_core,
    walk_visible_paths_via_folders_async,
)
from unique_toolkit.experimental.components.content_tree.schemas import (
    FolderWalkSnapshot,
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
    "extract_leaf_scope_ids_from_content_infos",
    "extract_scope_ids_from_content_infos",
    "format_path_trie",
    "FolderWalkSnapshot",
    "get_all_content_infos_async",
    "resolve_visible_file_paths_core",
    "translate_folder_path_async",
    "translate_folder_paths_async",
    "translate_scope_id_async",
    "translate_scope_ids_async",
    "translate_scope_ids_batch",
    "walk_visible_paths_via_folders_async",
]
