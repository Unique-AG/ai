"""Convenience re-export; implementation in :mod:`..components.content_tree`."""

from __future__ import annotations

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
