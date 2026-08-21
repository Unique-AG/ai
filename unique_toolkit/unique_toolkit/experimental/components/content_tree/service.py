"""The :class:`ContentTree` service.

Builds a filesystem-style view of knowledge-base folders and files the acting
user can see.

- **Folder-walk methods** — :meth:`ContentTree.resolve_visible_file_paths_via_folders_async`
  and :meth:`ContentTree.render_visible_tree_via_folders_async` expose
  ``max_depth``, ``timeout``, and :class:`FolderWalkSnapshot`.
- **Deprecated methods** — :meth:`ContentTree.resolve_visible_file_paths_async`
  and :meth:`ContentTree.render_visible_tree_async` keep the original
  signatures and still work; they call the folder-walk methods.

The service is intentionally **decoupled** from
:class:`~unique_toolkit.services.knowledge_base.KnowledgeBaseService`: it talks
to the same backend through the functional helpers in
:mod:`unique_toolkit.experimental.components.content_tree.functions` so it can be constructed and used
on its own.
"""

from __future__ import annotations

import asyncio
import functools
import json
import re
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Protocol, Self, overload

from rapidfuzz import fuzz
from typing_extensions import deprecated

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.experimental.components.content_tree.functions import (
    build_trie_from_resolved_paths,
    serialize_filter,
    walk_visible_paths_via_folders_async,
)
from unique_toolkit.experimental.components.content_tree.schemas import (
    FolderWalkSnapshot,
    FuzzyMatch,
    MatchTarget,
    PathTrieNode,
)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueContext


_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9]+")
_TRAILING_EXTENSION_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")


def _tokenize_for_fuzzy_scoring(
    value: str, case_sensitive: bool, *, strip_extension: bool = False
) -> str:
    """Normalize ``value`` into whitespace-separated tokens for
    :func:`rapidfuzz.fuzz.token_set_ratio`, which only tokenizes on
    whitespace — filenames/paths use ``_``/``-``/``/`` (and other
    punctuation) as their real word separators, so those need converting to
    spaces first or every candidate is scored as a single opaque token (no
    better than a plain char-ratio). Mirrors what
    :func:`rapidfuzz.utils.default_process` does, minus the unconditional
    lowercasing it bundles in — kept as a local regex rather than that
    helper (via ``fuzz.token_set_ratio``'s ``processor=`` argument) so
    ``case_sensitive=True`` can still skip lowercasing while keeping
    separator normalization.
    """
    if strip_extension:
        value = _TRAILING_EXTENSION_RE.sub("", value)
    if not case_sensitive:
        value = value.lower()
    return _NON_ALNUM_RE.sub(" ", value).strip()


class _CachedFolderWalkTaskFactory(Protocol):
    """``functools.cache`` wrapper around the folder-walk snapshot factory."""

    def __call__(
        self,
        filter_key: str,
        max_depth_key: int,
        max_concurrent_directory_listings: int,
    ) -> asyncio.Task[FolderWalkSnapshot]: ...

    def cache_clear(self) -> None: ...


class ContentTree:
    """Resolve visible content paths, render trees, and search files.

    The service is a thin orchestrator around the functional helpers in
    :mod:`unique_toolkit.experimental.components.content_tree.functions`. It takes the same identity
    parameters as the other toolkit services (``company_id`` / ``user_id`` /
    optional ``metadata_filter``) so it can be instantiated and tested without
    a :class:`~unique_toolkit.services.knowledge_base.KnowledgeBaseService`.

    Identity is exposed through read-only :class:`property` accessors
    (:attr:`company_id`, :attr:`user_id`, :attr:`metadata_filter`), so the
    public shape of the service is frozen by the language itself — trying to
    assign ``tree.company_id = ...`` raises :class:`AttributeError`. Because
    identity is stable, :meth:`resolve_visible_file_paths_via_folders_async`
    memoizes the folder walk (keyed by filter, depth, and listing concurrency).
    The cache stores the
    :class:`asyncio.Task` so that concurrent cache-miss callers await the
    same in-flight fetch (single-flight) and subsequent callers reuse the
    already-resolved value. Call :meth:`invalidate_cache` after a known
    backend mutation (upload, delete, rename…) to force a re-fetch.
    """

    def __init__(
        self,
        company_id: str,
        user_id: str,
        metadata_filter: dict[str, Any] | None = None,
    ) -> None:
        [company_id, user_id] = validate_required_values([company_id, user_id])
        # Private, underscore-prefixed fields; public access is via the
        # read-only ``@property`` accessors below. Metadata filter is copied
        # defensively so the caller's dict cannot mutate our state later.
        self._company_id: str = company_id
        self._user_id: str = user_id
        self._metadata_filter: dict[str, Any] | None = (
            None if metadata_filter is None else dict(metadata_filter)
        )

        # Bind ``functools.cache`` per-instance so each service has its own
        # task cache (class-level binding would leak across instances). The
        # cached factory returns an :class:`asyncio.Task`: concurrent misses
        # hit the same task → single-flight for free, stdlib-only.
        self._folder_walk_task: _CachedFolderWalkTaskFactory = functools.cache(
            self._create_folder_walk_task
        )
        self._folder_walk_progress: dict[tuple[str, int, int], FolderWalkSnapshot] = {}

    # ── Read-only identity (frozen via the property mechanic) ────────────

    @property
    def company_id(self) -> str:
        """Confidential company id this service is bound to."""
        return self._company_id

    @property
    def user_id(self) -> str:
        """Confidential user id this service is bound to."""
        return self._user_id

    @property
    def metadata_filter(self) -> dict[str, Any] | None:
        """Default metadata filter applied to content listings.

        Returned as a shallow copy to preserve the service's internal
        invariant that the stored filter is never mutated in place.
        """
        return None if self._metadata_filter is None else dict(self._metadata_filter)

    # ── Construction ─────────────────────────────────────────────────────

    @overload
    @classmethod
    def from_context(cls, context: UniqueContext) -> Self: ...

    @overload
    @classmethod
    def from_context(
        cls, context: UniqueContext, metadata_filter: dict[str, Any]
    ) -> Self: ...

    @classmethod
    def from_context(
        cls, context: UniqueContext, metadata_filter: dict[str, Any] | None = None
    ) -> Self:
        """Create from a :class:`UniqueContext` (preferred constructor)."""

        if metadata_filter is None:
            metadata_filter = (
                context.chat.metadata_filter if context.chat is not None else None
            )

        return cls(
            company_id=context.auth.get_confidential_company_id(),
            user_id=context.auth.get_confidential_user_id(),
            metadata_filter=metadata_filter,
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings | str | None = None,
        metadata_filter: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Self:
        """Create from :class:`UniqueSettings` (used by :class:`UniqueServiceFactory`)."""
        _ = kwargs

        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        elif isinstance(settings, str):
            settings = UniqueSettings.from_env_auto_with_sdk_init(filename=settings)

        if metadata_filter is None and settings.context.chat is not None:
            metadata_filter = settings.context.chat.metadata_filter

        return cls(
            company_id=settings.authcontext.get_confidential_company_id(),
            user_id=settings.authcontext.get_confidential_user_id(),
            metadata_filter=metadata_filter,
        )

    # ── Trie ─────────────────────────────────────────────────────────────

    @staticmethod
    def build_trie_from_resolved_paths(
        resolved: list[tuple[ContentInfo, PurePosixPath]],
        *,
        extra_folder_paths: list[PurePosixPath] | None = None,
    ) -> PathTrieNode:
        """Insert each ``(content, path)`` into a trie."""
        return build_trie_from_resolved_paths(
            resolved, extra_folder_paths=extra_folder_paths
        )

    # ── Cache management ─────────────────────────────────────────────────

    def invalidate_cache(self) -> None:
        """Clear the memoized folder-walk cache.

        Identity is frozen, so the cache never auto-invalidates during the
        instance's lifetime. Call this after an external mutation to the
        knowledge base (upload, delete, folder rename, …) when the next read
        must reflect that change.
        """
        self._folder_walk_task.cache_clear()
        self._folder_walk_progress.clear()

    def _create_folder_walk_task(
        self,
        filter_key: str,
        max_depth_key: int,
        max_concurrent_directory_listings: int,
    ) -> asyncio.Task[FolderWalkSnapshot]:
        """Build the cached folder-walk task.

        ``max_depth_key`` is ``-1`` when ``max_depth`` is ``None`` so the
        cache key stays hashable. The walk itself is never given a timeout:
        callers bound only their wait, so a timed-out evaluate can still let
        this task fill the cache.
        """
        effective_filter: dict[str, Any] | None = (
            None if filter_key == "null" else json.loads(filter_key)
        )
        max_depth = None if max_depth_key < 0 else max_depth_key
        progress = FolderWalkSnapshot(files=[], folder_paths=[], complete=False)
        self._folder_walk_progress[
            (filter_key, max_depth_key, max_concurrent_directory_listings)
        ] = progress
        return asyncio.ensure_future(
            walk_visible_paths_via_folders_async(
                user_id=self._user_id,
                company_id=self._company_id,
                metadata_filter=effective_filter,
                max_depth=max_depth,
                max_concurrent_directory_listings=max_concurrent_directory_listings,
                progress=progress,
            )
        )

    async def _await_folder_walk_task(
        self,
        task: asyncio.Task[FolderWalkSnapshot],
        progress: FolderWalkSnapshot,
        *,
        timeout: float | None,
    ) -> FolderWalkSnapshot:
        """Wait for a cached walk, returning a partial copy on timeout.

        ``asyncio.shield`` keeps the cached task running so a later call
        without ``timeout`` (or with a longer budget) receives the full tree.
        Waiter cancellation does not clear the cache; only a failed walk does.
        """
        try:
            if timeout is None:
                return await asyncio.shield(task)
            async with asyncio.timeout(timeout):
                return await asyncio.shield(task)
        except TimeoutError:
            return progress.copy(complete=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.invalidate_cache()
            raise

    # ── Folder-walk API (snapshot, depth, timeout) ───────────────────────

    async def resolve_visible_file_paths_via_folders_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_depth: int | None = None,
        timeout: float | None = None,
        max_concurrent_directory_listings: int = 25,
    ) -> FolderWalkSnapshot:
        """Walk ``Folder.get_infos`` and return files plus empty-folder prefixes.

        Cached per ``(metadata_filter, max_depth, concurrency)``. ``timeout``
        bounds only this wait; the cached walk keeps running.

        Args:
            metadata_filter (dict[str, Any] | None): UniqueQL filter for
                per-folder content listings. Falls back to the filter
                provided at construction time.
            max_depth (int | None): Stop recursion below this depth
                (``None`` = full walk).
            timeout (float | None): Seconds to wait before returning the
                rows collected so far. ``None`` waits until the walk
                finishes.
            max_concurrent_directory_listings (int): Bound on concurrent
                directory visits.

        Returns:
            FolderWalkSnapshot: File rows and visited folder prefixes.
            ``complete`` is ``False`` when ``timeout`` elapsed first.
        """
        effective_filter = (
            metadata_filter if metadata_filter is not None else self._metadata_filter
        )
        filter_key = serialize_filter(effective_filter)
        max_depth_key = -1 if max_depth is None else max_depth
        cache_key = (filter_key, max_depth_key, max_concurrent_directory_listings)
        task = self._folder_walk_task(*cache_key)
        progress = self._folder_walk_progress[cache_key]
        return await self._await_folder_walk_task(task, progress, timeout=timeout)

    async def render_visible_tree_via_folders_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_depth: int | None = None,
        timeout: float | None = None,
        max_concurrent_directory_listings: int = 25,
        show_files: bool = True,
    ) -> str:
        """Render a ``tree``-style string by walking folder listings.

        ``max_depth`` stops the walk (not only the printer). Empty directories
        appear. ``timeout`` returns whatever has been listed so far
        (``complete=False`` on the underlying snapshot) while the cached walk
        continues.

        Args:
            metadata_filter (dict[str, Any] | None): UniqueQL filter for
                per-folder content listings. Falls back to the filter
                provided at construction time.
            max_depth (int | None): Maximum directory depth under the
                synthetic root (``None`` = unlimited). Depth ``1`` lists only
                top-level folders and files. Mirrors ``tree -L``.
            timeout (float | None): Seconds to wait before rendering a
                partial tree. ``None`` waits until the walk finishes.
            max_concurrent_directory_listings (int): Bound on concurrent
                directory visits.
            show_files (bool): If ``False``, print directories only
                (``tree -d``).

        Returns:
            str: Multi-line ``tree(1)``-style rendering from
            :meth:`FolderWalkSnapshot.render`.
        """
        snapshot = await self.resolve_visible_file_paths_via_folders_async(
            metadata_filter=metadata_filter,
            max_depth=max_depth,
            timeout=timeout,
            max_concurrent_directory_listings=max_concurrent_directory_listings,
        )
        return snapshot.render(max_depth=max_depth, show_files=show_files)

    # ── Deprecated original API (still valid) ────────────────────────────

    @deprecated(
        "Use resolve_visible_file_paths_via_folders_async; it returns "
        "FolderWalkSnapshot with PurePosixPath rows, max_depth, and timeout."
    )
    async def resolve_visible_file_paths_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> list[tuple[ContentInfo, list[str]]]:
        """Return each visible file with path segments as a list of strings.

        Deprecated wrapper around
        :meth:`resolve_visible_file_paths_via_folders_async`. Callers that
        unpack ``(content_info, segments)`` and ``"/".join(segments)`` keep
        working.

        Args:
            metadata_filter (dict[str, Any] | None): UniqueQL filter for
                per-folder content listings. Falls back to the filter
                provided at construction time.
            max_concurrent_scope_lookups (int): Bound on concurrent directory
                visits.

        Returns:
            list[tuple[ContentInfo, list[str]]]: Each file paired with POSIX
            path segments (``["Legal", "Contracts", "nda.pdf"]``).
        """
        snapshot = await self.resolve_visible_file_paths_via_folders_async(
            metadata_filter=metadata_filter,
            max_concurrent_directory_listings=max_concurrent_scope_lookups,
        )
        return [
            (content_info, [part for part in path.parts if part != "."])
            for content_info, path in snapshot.files
        ]

    @deprecated(
        "Use render_visible_tree_via_folders_async; it adds timeout and "
        "show_files, and max_depth stops the folder walk."
    )
    async def render_visible_tree_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_depth: int | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> str:
        """Render a ``tree``-style string of visible folders and files.

        Deprecated wrapper around
        :meth:`render_visible_tree_via_folders_async`. ``max_depth`` stops the
        folder walk (``tree -L``), not only the printer.

        Args:
            metadata_filter (dict[str, Any] | None): UniqueQL filter for
                per-folder content listings. Falls back to the filter
                provided at construction time.
            max_depth (int | None): Maximum directory depth under the
                synthetic root (``None`` = unlimited).
            max_concurrent_scope_lookups (int): Bound on concurrent directory
                visits.

        Returns:
            str: Multi-line ``tree(1)``-style rendering.
        """
        return await self.render_visible_tree_via_folders_async(
            metadata_filter=metadata_filter,
            max_depth=max_depth,
            max_concurrent_directory_listings=max_concurrent_scope_lookups,
        )

    # ── Flat queries over the cached snapshot ────────────────────────────

    async def list_visible_files_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> list[ContentInfo]:
        """Return every visible file as a flat list of :class:`ContentInfo`.

        Reuses the cached snapshot from
        :meth:`resolve_visible_file_paths_via_folders_async`, so this is
        essentially free after the first call for a given key.
        """
        snapshot = await self.resolve_visible_file_paths_via_folders_async(
            metadata_filter=metadata_filter,
            max_concurrent_directory_listings=max_concurrent_scope_lookups,
        )
        return [content_info for content_info, _path in snapshot]

    async def filter_visible_files_async(
        self,
        predicate: Callable[[ContentInfo], bool],
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> list[ContentInfo]:
        """Client-side filter over the cached snapshot.

        Use for metadata predicates that the server-side ``metadata_filter``
        cannot express (e.g. computed attributes, regex over keys, combined
        conditions across fields). For server-expressible filters prefer
        ``metadata_filter`` — it's cheaper because fewer rows come back.

        Args:
            predicate: A callable returning ``True`` for files to keep.
            metadata_filter: Server-side filter forwarded to the listing call.
            max_concurrent_scope_lookups: Bound on concurrent directory visits.

        Returns:
            Every visible :class:`ContentInfo` for which ``predicate`` is truthy,
            preserving the underlying listing order.
        """
        files = await self.list_visible_files_async(
            metadata_filter=metadata_filter,
            max_concurrent_scope_lookups=max_concurrent_scope_lookups,
        )
        return [content_info for content_info in files if predicate(content_info)]

    async def search_visible_files_fuzzy_async(
        self,
        query: str,
        *,
        limit: int = 10,
        min_score: float = 0.6,
        match_on: MatchTarget = "both",
        case_sensitive: bool = False,
        metadata_filter: dict[str, Any] | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> list[FuzzyMatch]:
        """Fuzzy-match ``query`` against visible file names and/or paths.

        Scoring uses :func:`rapidfuzz.fuzz.token_set_ratio` over each string's
        tokens (split on whitespace, ``_``, ``-``, and ``/``, extension
        stripped), scaled to ``[0.0, 1.0]``. Token-set scoring means a short
        query that's a complete word inside a much longer filename scores
        highly (ideally ``1.0`` for an exact token match) instead of being
        penalized for the filename's unrelated length — a plain character-level
        ratio (e.g. :class:`difflib.SequenceMatcher`, used here previously)
        scores "alpensys" vs. "alpensys_budget_vs_actual_q3_2024.docx" at only
        ~0.35, indistinguishable from genuinely unrelated files, because it
        penalizes every unmatched character in the (much longer) candidate.
        Matching is case-insensitive by default since file names in a
        knowledge base tend to be noisy.

        Args:
            query: The search string (typically a fragment of a filename or path).
            limit: Maximum number of matches to return, after sorting by score
                descending.
            min_score: Drop matches scoring below this threshold.
            match_on: Score against the basename (``"key"``), the joined folder
                path (``"path"``), or take the max of both (``"both"``).
            case_sensitive: If ``False`` (default) both sides are lowercased
                before scoring.
            metadata_filter: Server-side filter forwarded to the listing call.
            max_concurrent_scope_lookups: Bound on concurrent directory visits.

        Returns:
            :class:`FuzzyMatch` records sorted by descending score, capped at
            ``limit``. Empty list if the query is empty or nothing clears
            ``min_score``.
        """
        if not query:
            return []

        snapshot = await self.resolve_visible_file_paths_via_folders_async(
            metadata_filter=metadata_filter,
            max_concurrent_directory_listings=max_concurrent_scope_lookups,
        )
        normalized_query = _tokenize_for_fuzzy_scoring(query, case_sensitive)

        matches: list[FuzzyMatch] = []
        for content_info, file_path in snapshot:
            key_candidate = _tokenize_for_fuzzy_scoring(
                content_info.key, case_sensitive, strip_extension=True
            )
            path_candidate = _tokenize_for_fuzzy_scoring(
                file_path.as_posix(), case_sensitive
            )

            score_key = match_on in ("key", "both")
            score_path = match_on in ("path", "both")
            key_score = (
                fuzz.token_set_ratio(normalized_query, key_candidate) / 100.0
                if score_key
                else 0.0
            )
            path_score = (
                fuzz.token_set_ratio(normalized_query, path_candidate) / 100.0
                if score_path
                else 0.0
            )

            if score_key and (not score_path or key_score >= path_score):
                score, matched_on = key_score, "key"
            else:
                score, matched_on = path_score, "path"

            if score >= min_score:
                matches.append(
                    FuzzyMatch(
                        content_info=content_info,
                        score=score,
                        path_segments=[part for part in file_path.parts if part != "."],
                        matched_on=matched_on,
                    )
                )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]
