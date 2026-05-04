"""Convenience re-export; implementation in :mod:`..components.content_tree`."""

from __future__ import annotations

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
