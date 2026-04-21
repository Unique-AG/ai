"""The :class:`ContentTree` service.

Builds a filesystem-style view of knowledge-base content visible to the acting
user (via ``folderIdPath`` metadata) and exposes it through three lenses:

- **Tree rendering** — :meth:`ContentTree.render_visible_tree_async` (``tree(1)``-style string).
- **Flat iteration / filtering** — :meth:`ContentTree.list_visible_files_async`,
  :meth:`ContentTree.filter_visible_files_async`.
- **Fuzzy file search** — :meth:`ContentTree.search_visible_files_fuzzy_async`
  over basenames and/or resolved folder paths.

The service is intentionally **decoupled** from
:class:`~unique_toolkit.services.knowledge_base.KnowledgeBaseService`: it talks
to the same backend through the functional helpers in
:mod:`unique_toolkit.experimental.content_tree.functions` so it can be constructed and used
on its own.
"""

from __future__ import annotations

import asyncio
import difflib
import functools
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, Self, overload

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.experimental.content_tree.functions import (
    build_trie_from_resolved_paths,
    format_path_trie,
    resolve_visible_file_paths_core,
    serialize_filter,
)
from unique_toolkit.experimental.content_tree.schemas import (
    FuzzyMatch,
    MatchTarget,
    PathTrieNode,
)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueContext


class _CachedResolveTaskFactory(Protocol):
    """Structural type for :func:`functools.cache`-wrapped resolve-task factory.

    :func:`functools.cache` returns a ``_lru_cache_wrapper`` that exposes
    ``cache_clear`` / ``cache_info`` in addition to being callable. Static
    checkers see the return annotation as a plain ``Callable`` and reject the
    attribute access; this Protocol captures the real runtime shape so we can
    type ``cache_clear`` without a per-call ``type: ignore``.
    """

    def __call__(
        self,
        filter_key: str,
        max_concurrent_scope_lookups: int,
    ) -> asyncio.Task[list[tuple[ContentInfo, list[str]]]]: ...

    def cache_clear(self) -> None: ...


class ContentTree:
    """Resolve visible content paths, render trees, and search files.

    The service is a thin orchestrator around the functional helpers in
    :mod:`unique_toolkit.experimental.content_tree.functions`. It takes the same identity
    parameters as the other toolkit services (``company_id`` / ``user_id`` /
    optional ``metadata_filter``) so it can be instantiated and tested without
    a :class:`~unique_toolkit.services.knowledge_base.KnowledgeBaseService`.

    Identity is exposed through read-only :class:`property` accessors
    (:attr:`company_id`, :attr:`user_id`, :attr:`metadata_filter`), so the
    public shape of the service is frozen by the language itself — trying to
    assign ``tree.company_id = ...`` raises :class:`AttributeError`. Because
    identity is stable, :meth:`resolve_visible_file_paths_async` memoizes its
    result per-instance via :func:`functools.cache`. The cache stores the
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
        self._resolve_task: _CachedResolveTaskFactory = functools.cache(
            self._create_resolve_task
        )

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
        resolved: list[tuple[ContentInfo, list[str]]],
    ) -> PathTrieNode:
        """Insert each ``(content, [dir, ..., filename])`` into a trie."""
        return build_trie_from_resolved_paths(resolved)

    # ── Cache management ─────────────────────────────────────────────────

    def invalidate_cache(self) -> None:
        """Clear the memoized resolved-paths cache.

        Identity is frozen, so the cache never auto-invalidates during the
        instance's lifetime. Call this after an external mutation to the
        knowledge base (upload, delete, folder rename, …) when the next read
        must reflect that change.
        """
        self._resolve_task.cache_clear()

    def _create_resolve_task(
        self,
        filter_key: str,
        max_concurrent_scope_lookups: int,
    ) -> asyncio.Task[list[tuple[ContentInfo, list[str]]]]:
        """Build the :class:`asyncio.Task` cached per ``(filter, concurrency)``.

        ``filter_key`` is the :func:`serialize_filter` output of the effective
        metadata filter. We reconstitute the dict here so the hot-path caller
        does not need to re-parse on every hit.
        """
        effective_filter: dict[str, Any] | None = (
            None if filter_key == "null" else json.loads(filter_key)
        )
        return asyncio.ensure_future(
            resolve_visible_file_paths_core(
                user_id=self._user_id,
                company_id=self._company_id,
                metadata_filter=effective_filter,
                max_concurrent_scope_lookups=max_concurrent_scope_lookups,
            )
        )

    # ── Public async API ─────────────────────────────────────────────────

    async def resolve_visible_file_paths_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> list[tuple[ContentInfo, list[str]]]:
        """Map each visible content item to path segments ``[folder, ..., filename]``.

        Results are memoized with :func:`functools.cache` keyed by the
        effective ``(metadata_filter, max_concurrent_scope_lookups)`` pair.
        Concurrent cache-miss calls await the same :class:`asyncio.Task` —
        the expensive fetch runs exactly once per key. On failure the whole
        task cache is dropped so the next call retries cleanly.
        """
        effective_filter = (
            metadata_filter if metadata_filter is not None else self._metadata_filter
        )
        filter_key = serialize_filter(effective_filter)
        task = self._resolve_task(filter_key, max_concurrent_scope_lookups)
        try:
            return await task
        except BaseException:
            self.invalidate_cache()
            raise

    async def render_visible_tree_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_depth: int | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> str:
        """Fetch visible paths and return a multi-line ``tree``-style string.

        Args:
            metadata_filter: Optional filter passed through to content listing.
                Falls back to the filter provided at construction time.
            max_depth: Maximum directory depth under the synthetic root
                (``None`` = unlimited). Depth ``1`` lists only top-level
                folders/files. Mirrors ``tree -L``.
            max_concurrent_scope_lookups: Concurrency when resolving scope ids
                to names.
        """
        rows = await self.resolve_visible_file_paths_async(
            metadata_filter=metadata_filter,
            max_concurrent_scope_lookups=max_concurrent_scope_lookups,
        )
        trie = build_trie_from_resolved_paths(rows)
        return format_path_trie(trie, max_depth=max_depth)

    # ── Flat queries over the cached snapshot ────────────────────────────

    async def list_visible_files_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        max_concurrent_scope_lookups: int = 25,
    ) -> list[ContentInfo]:
        """Return every visible file as a flat list of :class:`ContentInfo`.

        Reuses the cached snapshot from
        :meth:`resolve_visible_file_paths_async`, so this is essentially free
        after the first call for a given ``metadata_filter``.
        """
        rows = await self.resolve_visible_file_paths_async(
            metadata_filter=metadata_filter,
            max_concurrent_scope_lookups=max_concurrent_scope_lookups,
        )
        return [content_info for content_info, _segments in rows]

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
            max_concurrent_scope_lookups: Concurrency for scope-id resolution.

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

        Scoring uses :class:`difflib.SequenceMatcher` (stdlib), which returns a
        ratio in ``[0.0, 1.0]``. Matching is case-insensitive by default since
        file names in a knowledge base tend to be noisy.

        Args:
            query: The search string (typically a fragment of a filename or path).
            limit: Maximum number of matches to return, after sorting by score
                descending.
            min_score: Drop matches scoring below this threshold. ``0.6`` is
                :mod:`difflib`'s own rule of thumb for "reasonably close".
            match_on: Score against the basename (``"key"``), the joined folder
                path (``"path"``), or take the max of both (``"both"``).
            case_sensitive: If ``False`` (default) both sides are lowercased
                before scoring.
            metadata_filter: Server-side filter forwarded to the listing call.
            max_concurrent_scope_lookups: Concurrency for scope-id resolution.

        Returns:
            :class:`FuzzyMatch` records sorted by descending score, capped at
            ``limit``. Empty list if the query is empty or nothing clears
            ``min_score``.
        """
        if not query:
            return []

        rows = await self.resolve_visible_file_paths_async(
            metadata_filter=metadata_filter,
            max_concurrent_scope_lookups=max_concurrent_scope_lookups,
        )
        normalized_query = query if case_sensitive else query.lower()

        matches: list[FuzzyMatch] = []
        for content_info, segments in rows:
            key_candidate = content_info.key
            path_candidate = "/".join(segments)
            if not case_sensitive:
                key_candidate = key_candidate.lower()
                path_candidate = path_candidate.lower()

            score_key = match_on in ("key", "both")
            score_path = match_on in ("path", "both")
            key_score = (
                difflib.SequenceMatcher(None, normalized_query, key_candidate).ratio()
                if score_key
                else 0.0
            )
            path_score = (
                difflib.SequenceMatcher(None, normalized_query, path_candidate).ratio()
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
                        path_segments=list(segments),
                        matched_on=matched_on,
                    )
                )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]
