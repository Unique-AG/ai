"""Data classes for the content-tree subpackage.

These types describe the *shape* of a content-tree snapshot:

- :class:`PathTrieNode` is the in-memory directory structure built from resolved
  file paths.
- :class:`FuzzyMatch` is the result record returned by
  :meth:`unique_toolkit.experimental.components.content_tree.service.ContentTree.search_visible_files_fuzzy_async`.

Kept free of behaviour so they can be imported and introspected without pulling
in the SDK/HTTP stack used by :mod:`unique_toolkit.experimental.components.content_tree.functions`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from unique_toolkit.content.schemas import ContentInfo

MatchTarget = Literal["key", "path", "both"]
"""Which representation of a file a fuzzy query is scored against.

- ``"key"``  — only the basename (``content_info.key``)
- ``"path"`` — only the slash-joined resolved folder path ``"a/b/c.pdf"``
- ``"both"`` — score against both and keep the higher of the two
"""


@dataclass
class PathTrieNode:
    """Nested directory structure; ``files`` are basenames in this directory."""

    children: dict[str, PathTrieNode] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)

    def walk_trie_nodes(self) -> list[PathTrieNode]:
        out: list[PathTrieNode] = [self]
        for child in self.children.values():
            out.extend(child.walk_trie_nodes())
        return out

    def format_trie_walk(
        self,
        *,
        prefix: str,
        depth: int,
        max_depth: int | None,
        lines: list[str] | None = None,
    ) -> list[str]:
        if lines is None:
            lines = ["."]

        if max_depth is not None and depth >= max_depth:
            descendants = self.walk_trie_nodes()
            # Exclude ``self`` from the directory count; the summary describes
            # what is hidden *below* the cutoff, not the truncated node itself.
            hidden_dirs = len(descendants) - 1
            hidden_files = sum(len(node.files) for node in descendants)
            if hidden_dirs or hidden_files:
                lines.append(
                    f"{prefix}… ({hidden_dirs} dirs, {hidden_files} files below)"
                )
            return lines

        dir_items = sorted(self.children.items())
        file_items = [(name, None) for name in sorted(self.files)]
        entries: list[tuple[str, PathTrieNode | None, bool]] = [
            (name, child, True) for name, child in dir_items
        ]
        entries.extend((name, None, False) for name, _ in file_items)

        for i, (name, child, is_dir) in enumerate(entries):
            is_last = i == len(entries) - 1
            branch = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "
            lines.append(f"{prefix}{branch}{name}")
            if is_dir and child is not None:
                child.format_trie_walk(
                    prefix=prefix + extension,
                    depth=depth + 1,
                    max_depth=max_depth,
                    lines=lines,
                )

        return lines


@dataclass(frozen=True)
class FuzzyMatch:
    """A single hit from :meth:`ContentTree.search_visible_files_fuzzy_async`.

    Attributes:
        content_info: The matched file.
        score: Similarity score in ``[0.0, 1.0]``; ``1.0`` is an exact match.
        path_segments: Full resolved path as segments ``[folder, ..., filename]``.
            Callers that want a displayable string can ``"/".join(...)`` it.
        matched_on: Whether the winning score came from matching the basename
            (``"key"``) or the joined folder path (``"path"``). Always set, even
            when ``match_on="both"`` was requested.
    """

    content_info: ContentInfo
    score: float
    path_segments: list[str]
    matched_on: Literal["key", "path"]
