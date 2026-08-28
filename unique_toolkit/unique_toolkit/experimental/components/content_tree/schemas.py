"""Data classes for the content-tree subpackage.

These types describe the *shape* of a content-tree snapshot:

- Knowledge-base locations are :class:`~pathlib.PurePosixPath` values
  (``Legal/Contracts/nda.pdf``). ``.parent`` is the folder path, ``.name`` is
  the filename. POSIX form is used so Windows does not inject ``\\``.
- :class:`PathTrieNode` is the in-memory directory structure built from those
  paths.
- :class:`FolderWalkSnapshot` is the result of walking ``Folder.get_infos`` +
  ``Content.get_infos(parentId)``. It can render itself as a ``tree(1)`` string.
- :class:`FuzzyMatch` is the result record returned by
  :meth:`unique_toolkit.experimental.components.content_tree.service.ContentTree.search_visible_files_fuzzy_async`.

Trie building and rendering live here so they can be used without the SDK/HTTP
stack in :mod:`unique_toolkit.experimental.components.content_tree.functions`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Literal, overload

from unique_toolkit.content.schemas import ContentInfo

MatchTarget = Literal["key", "path", "both"]
"""Which representation of a file a fuzzy query is scored against.

- ``"key"``  — only the basename (``content_info.key``)
- ``"path"`` — only the slash-joined resolved folder path ``"a/b/c.pdf"``
- ``"both"`` — score against both and keep the higher of the two
"""


def _posix_parts(path: PurePosixPath) -> tuple[str, ...]:
    """Path parts, dropping the ``.`` that :class:`~pathlib.PurePosixPath` uses for empty."""
    return tuple(part for part in path.parts if part != ".")


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
        show_files: bool = True,
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
            if hidden_dirs or (show_files and hidden_files):
                if show_files:
                    summary = f"{hidden_dirs} dirs, {hidden_files} files below"
                else:
                    summary = f"{hidden_dirs} dirs below"
                lines.append(f"{prefix}… ({summary})")
            return lines

        dir_items = sorted(self.children.items())
        entries: list[tuple[str, PathTrieNode | None, bool]] = [
            (name, child, True) for name, child in dir_items
        ]
        if show_files:
            entries.extend((name, None, False) for name in sorted(self.files))

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
                    show_files=show_files,
                    lines=lines,
                )

        return lines

    def render(self, *, max_depth: int | None = None, show_files: bool = True) -> str:
        """Render this node as a GNU ``tree(1)``-style string.

        Args:
            max_depth (int | None): Truncate printed depth (``None`` = full
                tree). Mirrors ``tree -L``.
            show_files (bool): If ``False``, print directories only
                (``tree -d``).

        Returns:
            str: Multi-line UTF-8 box-drawing tree, rooted at ``.``.
        """
        lines = self.format_trie_walk(
            prefix="",
            depth=0,
            max_depth=max_depth,
            show_files=show_files,
            lines=None,
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class FuzzyMatch:
    """A single hit from :meth:`ContentTree.search_visible_files_fuzzy_async`.

    Attributes:
        content_info: The matched file.
        score: Similarity score in ``[0.0, 1.0]``; ``1.0`` is an exact match.
        path_segments: Folder names plus basename, as a list of strings
            (``["Legal", "Contracts", "nda.pdf"]``). Join with ``"/"`` for a
            display path.
        matched_on: Whether the winning score came from matching the basename
            (``"key"``) or the joined folder path (``"path"``). Always set, even
            when ``match_on="both"`` was requested.
    """

    content_info: ContentInfo
    score: float
    path_segments: list[str]
    matched_on: Literal["key", "path"]

    @property
    def path(self) -> PurePosixPath:
        """``path_segments`` as a :class:`~pathlib.PurePosixPath`."""
        return (
            PurePosixPath(*self.path_segments)
            if self.path_segments
            else PurePosixPath()
        )


@dataclass
class FolderWalkSnapshot(Sequence[tuple[ContentInfo, PurePosixPath]]):
    """Files and folder prefixes collected by a ``Folder.get_infos`` walk.

    Iterating the snapshot yields ``(content_info, path)`` rows.

    Attributes:
        files: Each visible file paired with its knowledge-base
            :class:`~pathlib.PurePosixPath` (``.parent`` is the folder,
            ``.name`` is the filename).
        folder_paths: Every visited folder (including empty ones) from the
            knowledge-base root. Used so the trie can show directories that
            contain no files.
        complete: ``True`` when the walk finished. ``False`` when the caller
            timed out (or the walk was aborted) and this is a partial snapshot
            of directories listed so far.

    Call :meth:`render` (or ``str(snapshot)``) for a ``tree(1)``-style view.
    """

    files: list[tuple[ContentInfo, PurePosixPath]]
    folder_paths: list[PurePosixPath]
    complete: bool = True

    def __len__(self) -> int:
        return len(self.files)

    def __bool__(self) -> bool:
        """A snapshot is always truthy, even with no files yet."""
        return True

    @overload
    def __getitem__(self, index: int) -> tuple[ContentInfo, PurePosixPath]: ...

    @overload
    def __getitem__(self, index: slice) -> list[tuple[ContentInfo, PurePosixPath]]: ...

    def __getitem__(
        self, index: int | slice
    ) -> tuple[ContentInfo, PurePosixPath] | list[tuple[ContentInfo, PurePosixPath]]:
        return self.files[index]

    def copy(self, *, complete: bool | None = None) -> FolderWalkSnapshot:
        """Return a snapshot that later walk mutations will not affect.

        Args:
            complete (bool | None): Override ``complete`` on the copy.
                ``None`` keeps this instance's flag.

        Returns:
            FolderWalkSnapshot: Independent lists of files and folder prefixes.
        """
        return FolderWalkSnapshot(
            files=list(self.files),
            folder_paths=list(self.folder_paths),
            complete=self.complete if complete is None else complete,
        )

    def to_trie(self) -> PathTrieNode:
        """Build a directory trie from files and empty-folder prefixes.

        Returns:
            PathTrieNode: Nested folders and basenames for :meth:`render`.
        """
        root = PathTrieNode()
        for _content_info, path in self.files:
            parts = _posix_parts(path)
            if not parts:
                continue
            *dirs, filename = parts
            node = root
            for part in dirs:
                if part not in node.children:
                    node.children[part] = PathTrieNode()
                node = node.children[part]
            node.files.append(filename)
        for folder in self.folder_paths:
            parts = _posix_parts(folder)
            if not parts:
                continue
            node = root
            for part in parts:
                if part not in node.children:
                    node.children[part] = PathTrieNode()
                node = node.children[part]
        for node in root.walk_trie_nodes():
            node.files = sorted(set(node.files))
        return root

    def render(self, *, max_depth: int | None = None, show_files: bool = True) -> str:
        """Render a GNU ``tree(1)``-style string of this snapshot.

        Args:
            max_depth (int | None): Truncate printed depth (``None`` = everything
                already collected). Does not fetch more data.
            show_files (bool): If ``False``, print directories only
                (``tree -d``). Files stay in :attr:`files`.

        Returns:
            str: Multi-line UTF-8 box-drawing tree.
        """
        return self.to_trie().render(max_depth=max_depth, show_files=show_files)

    def __str__(self) -> str:
        """Same as :meth:`render` with no depth limit."""
        return self.render()
