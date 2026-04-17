"""Content-tree subpackage: visible-content listing, tree rendering, and fuzzy search.

Typical usage::

    from unique_toolkit.content.tree import ContentTree

    tree = ContentTree.from_settings()
    print(await tree.render_visible_tree_async(max_depth=2))
    hits = await tree.search_visible_files_fuzzy_async("annual_report")

The subpackage is split into three modules to mirror the rest of the
``content`` domain:

- :mod:`unique_toolkit.content.tree.schemas` — data classes (:class:`PathTrieNode`,
  :class:`FuzzyMatch`, :data:`MatchTarget`).
- :mod:`unique_toolkit.content.tree.functions` — pure helpers for listing,
  scope-id resolution, trie construction, and ``tree(1)``-style formatting.
- :mod:`unique_toolkit.content.tree.service` — :class:`ContentTree`, the
  orchestrating service with per-instance caching.
"""

from unique_toolkit.content.tree.functions import (
    build_trie_from_resolved_paths as build_trie_from_resolved_paths,
)
from unique_toolkit.content.tree.functions import (
    extract_scope_ids_from_content_infos as extract_scope_ids_from_content_infos,
)
from unique_toolkit.content.tree.functions import (
    format_path_trie as format_path_trie,
)
from unique_toolkit.content.tree.functions import (
    get_all_content_infos_async as get_all_content_infos_async,
)
from unique_toolkit.content.tree.functions import (
    resolve_visible_file_paths_core as resolve_visible_file_paths_core,
)
from unique_toolkit.content.tree.functions import (
    translate_scope_id_async as translate_scope_id_async,
)
from unique_toolkit.content.tree.functions import (
    translate_scope_ids_async as translate_scope_ids_async,
)
from unique_toolkit.content.tree.functions import (
    translate_scope_ids_batch as translate_scope_ids_batch,
)
from unique_toolkit.content.tree.schemas import (
    FuzzyMatch as FuzzyMatch,
)
from unique_toolkit.content.tree.schemas import (
    MatchTarget as MatchTarget,
)
from unique_toolkit.content.tree.schemas import (
    PathTrieNode as PathTrieNode,
)
from unique_toolkit.content.tree.service import (
    ContentTree as ContentTree,
)
