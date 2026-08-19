"""Unit tests for :class:`~unique_toolkit.experimental.components.content_tree.service.ContentTree`."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import PurePosixPath
from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.content.schemas import ContentInfo, PaginatedContentInfos
from unique_toolkit.experimental.content_tree import (
    ContentTree,
    FolderWalkSnapshot,
    FuzzyMatch,
    extract_leaf_scope_ids_from_content_infos,
    extract_scope_ids_from_content_infos,
    format_path_trie,
    walk_visible_paths_via_folders_async,
)

# All patches target the name as bound in ``experimental.components.content_tree.service``
# (where the service module imports it from ``functions``), not the original
# definition module. That's the usual ``mock.patch`` rule: patch where it's
# looked up. Old methods and via-folders methods share this walk.
_PATCH_TARGET = (
    "unique_toolkit.experimental.components.content_tree.service"
    ".walk_visible_paths_via_folders_async"
)
_WALK_PATCH = _PATCH_TARGET


def _p(*parts: str) -> PurePosixPath:
    """Knowledge-base path used in assertions and fixtures."""
    return PurePosixPath(*parts)


def _minimal_content_info(*, key: str, metadata: dict | None) -> ContentInfo:
    now = datetime.now(tz=UTC)
    return ContentInfo.model_construct(
        id=f"id-{key}",
        object="content",
        key=key,
        byte_size=0,
        mime_type="application/octet-stream",
        owner_id="owner",
        created_at=now,
        updated_at=now,
        metadata=metadata,
    )


def _walk_snapshot(
    rows: list[tuple[ContentInfo, PurePosixPath]] | None = None,
) -> FolderWalkSnapshot:
    return FolderWalkSnapshot(files=list(rows or []), folder_paths=[], complete=True)


def test_AI_build_trie_groups_path_segments() -> None:
    """Building a trie merges files under the correct folder chain."""
    resolved = [
        (
            _minimal_content_info(
                key="a.pdf",
                metadata={"folderIdPath": "uniquepathid://s1/s2"},
            ),
            _p("Scope1", "Scope2", "a.pdf"),
        ),
        (
            _minimal_content_info(
                key="b.pdf",
                metadata={"folderIdPath": "uniquepathid://s1/s2"},
            ),
            _p("Scope1", "Scope2", "b.pdf"),
        ),
    ]
    trie = ContentTree.build_trie_from_resolved_paths(resolved)
    assert sorted(trie.children["Scope1"].children["Scope2"].files) == [
        "a.pdf",
        "b.pdf",
    ]


def test_AI_build_trie_includes_empty_folders_from_extra_paths() -> None:
    """
    Purpose: Extra folder prefixes create trie nodes even without files.
    Why this matters: Folder-walk trees must show empty directories.
    Setup summary: Build a trie with no files and extra_folder_paths; assert nodes.
    """
    trie = ContentTree.build_trie_from_resolved_paths(
        [], extra_folder_paths=[_p("Legal", "Empty")]
    )
    assert "Empty" in trie.children["Legal"].children
    assert trie.children["Legal"].children["Empty"].files == []


def test_AI_format_path_trie_truncates_at_max_depth() -> None:
    """Depth-limited rendering omits deeper files (``tree -L`` semantics)."""
    trie = ContentTree.build_trie_from_resolved_paths(
        [
            (
                _minimal_content_info(key="deep.pdf", metadata=None),
                _p("top", "mid", "deep.pdf"),
            ),
        ]
    )
    out = format_path_trie(trie, max_depth=1)
    assert "deep.pdf" not in out
    assert "…" in out


def test_AI_format_path_trie_hidden_count_is_recursive() -> None:
    """Truncation summary counts all descendants, not only immediate children.

    Regression: the summary line says "below", so a deeply nested tree with
    many files under the cutoff must have them all counted — not just the
    direct children of the truncated node.
    """
    trie = ContentTree.build_trie_from_resolved_paths(
        [
            (
                _minimal_content_info(key="a.pdf", metadata=None),
                _p("top", "mid", "a.pdf"),
            ),
            (
                _minimal_content_info(key="b.pdf", metadata=None),
                _p("top", "mid", "b.pdf"),
            ),
            (
                _minimal_content_info(key="c.pdf", metadata=None),
                _p("top", "other", "nested", "c.pdf"),
            ),
        ]
    )
    out = format_path_trie(trie, max_depth=1)
    # Below ``top``: 3 dirs (mid, other, nested) and 3 files (a.pdf, b.pdf, c.pdf).
    assert "(3 dirs, 3 files below)" in out


@pytest.mark.ai
def test_AI_snapshot_render_includes_files_and_empty_folders() -> None:
    """
    Purpose: FolderWalkSnapshot.render draws files and empty directories.
    Why this matters: Callers should print a snapshot without building a trie.
    Setup summary: One file plus an empty folder prefix; assert both names appear.
    """
    snapshot = FolderWalkSnapshot(
        files=[
            (
                _minimal_content_info(key="a.pdf", metadata=None),
                _p("Legal", "a.pdf"),
            )
        ],
        folder_paths=[_p("Legal"), _p("Empty")],
    )
    rendered = snapshot.render()
    assert "a.pdf" in rendered
    assert "Legal" in rendered
    assert "Empty" in rendered
    assert str(snapshot) == rendered


@pytest.mark.ai
def test_AI_empty_snapshot_is_truthy() -> None:
    """
    Purpose: An empty FolderWalkSnapshot is still a real object in boolean context.
    Why this matters: Callers use ``progress or FolderWalkSnapshot(...)``; Sequence.__len__
        would make an empty walk look missing and drop partial timeout updates.
    Setup summary: Empty snapshot; assert bool is True and len is 0.
    """
    snapshot = FolderWalkSnapshot(files=[], folder_paths=[])
    assert bool(snapshot) is True
    assert len(snapshot) == 0


@pytest.mark.ai
def test_AI_snapshot_render_can_hide_files() -> None:
    """
    Purpose: show_files=False prints directories only, like tree -d.
    Why this matters: Folder orientation should not require listing every file.
    Setup summary: File under Legal plus empty folder; assert pdf omitted, dirs kept.
    """
    snapshot = FolderWalkSnapshot(
        files=[
            (
                _minimal_content_info(key="a.pdf", metadata=None),
                _p("Legal", "a.pdf"),
            )
        ],
        folder_paths=[_p("Legal"), _p("Empty")],
    )
    rendered = snapshot.render(show_files=False)
    assert "a.pdf" not in rendered
    assert "Legal" in rendered
    assert "Empty" in rendered


@pytest.mark.ai
def test_AI_snapshot_render_hide_files_omits_files_from_truncation_summary() -> None:
    """
    Purpose: Directories-only truncation does not mention hidden files.
    Why this matters: tree -d -L should not report file counts below the cutoff.
    Setup summary: Nested file; render max_depth=1 with show_files=False.
    """
    snapshot = FolderWalkSnapshot(
        files=[
            (
                _minimal_content_info(key="deep.pdf", metadata=None),
                _p("top", "mid", "deep.pdf"),
            )
        ],
        folder_paths=[],
    )
    out = snapshot.render(max_depth=1, show_files=False)
    assert "deep.pdf" not in out
    assert "files below" not in out
    assert "dirs below" in out


@pytest.mark.ai
def test_AI_snapshot_render_truncates_at_max_depth() -> None:
    """
    Purpose: snapshot.render(max_depth=) truncates print depth like tree -L.
    Why this matters: Depth on render must not require a separate trie helper.
    Setup summary: Nested file; assert basename is hidden at max_depth=1.
    """
    snapshot = FolderWalkSnapshot(
        files=[
            (
                _minimal_content_info(key="deep.pdf", metadata=None),
                _p("top", "mid", "deep.pdf"),
            )
        ],
        folder_paths=[],
    )
    out = snapshot.render(max_depth=1)
    assert "deep.pdf" not in out
    assert "…" in out


def test_AI_extract_scope_ids_matches_folder_id_path() -> None:
    """Scope id extraction strips the ``uniquepathid://`` prefix."""
    infos = [
        _minimal_content_info(
            key="x",
            metadata={"folderIdPath": "uniquepathid://aa/bb"},
        ),
    ]
    assert extract_scope_ids_from_content_infos(infos) == {"aa", "bb"}


@pytest.mark.ai
def test_AI_extract_leaf_scope_ids_keeps_only_last_segment() -> None:
    """
    Purpose: Leaf extraction returns only the last folderIdPath segment.
    Why this matters: Path resolution now does one API call per parent folder, not per ancestor.
    Setup summary: Two files sharing an ancestor but different leaves; assert only the two leaves.
    """
    infos = [
        _minimal_content_info(
            key="a.pdf",
            metadata={"folderIdPath": "uniquepathid://root/legal/contracts"},
        ),
        _minimal_content_info(
            key="b.pdf",
            metadata={"folderIdPath": "uniquepathid://root/legal/invoices"},
        ),
    ]
    assert extract_leaf_scope_ids_from_content_infos(infos) == {
        "contracts",
        "invoices",
    }


@pytest.mark.ai
def test_AI_extract_leaf_scope_ids_deduplicates_shared_parent() -> None:
    """
    Purpose: Files in the same folder produce a single leaf id.
    Why this matters: Duplicate leaves would re-fetch the same folder path.
    Setup summary: Two files with identical folderIdPath; assert one leaf.
    """
    infos = [
        _minimal_content_info(
            key="a.pdf",
            metadata={"folderIdPath": "uniquepathid://root/leaf"},
        ),
        _minimal_content_info(
            key="b.pdf",
            metadata={"folderIdPath": "uniquepathid://root/leaf"},
        ),
    ]
    assert extract_leaf_scope_ids_from_content_infos(infos) == {"leaf"}


# ── Freeze + cache behavior ─────────────────────────────────────────────────


def _tree(metadata_filter: dict | None = None) -> ContentTree:
    return ContentTree(company_id="c1", user_id="u1", metadata_filter=metadata_filter)


def test_AI_identity_properties_are_read_only() -> None:
    """Public identity is exposed via ``@property`` and rejects assignment.

    The cache on the service trusts identity to be stable, so the property
    mechanic is what language-level guarantees that stability for callers.
    """
    svc = _tree(metadata_filter={"env": "prod"})

    assert svc.company_id == "c1"
    assert svc.user_id == "u1"
    assert svc.metadata_filter == {"env": "prod"}

    for attr in ("company_id", "user_id", "metadata_filter"):
        with pytest.raises(AttributeError):
            setattr(svc, attr, "anything")


def test_AI_metadata_filter_property_returns_defensive_copy() -> None:
    """Mutating the dict returned from the property must not affect state."""
    svc = _tree(metadata_filter={"dept": "legal"})
    observed = svc.metadata_filter
    assert observed is not None
    observed["dept"] = "hr"
    assert svc.metadata_filter == {"dept": "legal"}


def test_AI_constructor_copies_metadata_filter_to_prevent_external_mutation() -> None:
    """Mutating the caller's dict after construction must not leak into state."""
    caller_filter = {"dept": "legal"}
    svc = _tree(metadata_filter=caller_filter)
    caller_filter["dept"] = "hr"
    assert svc.metadata_filter == {"dept": "legal"}


@pytest.mark.asyncio
async def test_AI_resolve_visible_file_paths_is_cached_across_calls() -> None:
    """A second call with the same args must not re-fetch from the backend."""
    svc = _tree()
    resolved = [
        (
            _minimal_content_info(key="a.pdf", metadata=None),
            _p("_no_folder_path", "a.pdf"),
        ),
    ]

    mock_core = AsyncMock(return_value=_walk_snapshot(resolved))
    with patch(_PATCH_TARGET, mock_core):
        first = await svc.resolve_visible_file_paths_async()
        second = await svc.resolve_visible_file_paths_async()

    assert first == second
    assert mock_core.await_count == 1


@pytest.mark.asyncio
@pytest.mark.ai
async def test_AI_resolve_visible_file_paths_returns_string_segments() -> None:
    """
    Purpose: The original resolve method returns list[str] path segments.
    Why this matters: Callers unpack ``(content_info, segments)`` and ``"/".join``.
    Setup summary: Patch the walk with a POSIX path; assert adapted rows.
    """
    svc = _tree()
    info = _minimal_content_info(key="nda.pdf", metadata=None)
    mock_core = AsyncMock(return_value=_walk_snapshot([(info, _p("Legal", "nda.pdf"))]))
    with patch(_PATCH_TARGET, mock_core):
        rows = await svc.resolve_visible_file_paths_async()

    assert isinstance(rows, list)
    assert rows == [(info, ["Legal", "nda.pdf"])]


@pytest.mark.asyncio
@pytest.mark.ai
@pytest.mark.filterwarnings("default::DeprecationWarning")
async def test_AI_resolve_visible_file_paths_async_emits_deprecation_warning() -> None:
    """
    Purpose: The original resolve method is deprecated in favor of via-folders.
    Why this matters: Callers should migrate without the old method disappearing.
    Setup summary: Call the deprecated method; expect DeprecationWarning.
    """
    svc = _tree()
    with patch(_PATCH_TARGET, AsyncMock(return_value=_walk_snapshot())):
        with pytest.warns(DeprecationWarning, match="via_folders"):
            await svc.resolve_visible_file_paths_async()


@pytest.mark.asyncio
async def test_AI_cache_keys_on_effective_metadata_filter() -> None:
    """Different effective filters must not collide in the cache."""
    svc = _tree(metadata_filter={"env": "prod"})

    mock_core = AsyncMock(
        side_effect=lambda **kw: _walk_snapshot(
            [
                (
                    _minimal_content_info(
                        key=f"for-{(kw.get('metadata_filter') or {}).get('env', 'none')}.pdf",
                        metadata=None,
                    ),
                    _p("_no_folder_path", "x.pdf"),
                )
            ]
        )
    )
    with patch(_PATCH_TARGET, mock_core):
        await svc.resolve_visible_file_paths_async()
        await svc.resolve_visible_file_paths_async(metadata_filter={"env": "dev"})
        await svc.resolve_visible_file_paths_async()

    assert mock_core.await_count == 2


@pytest.mark.asyncio
async def test_AI_invalidate_cache_forces_refetch() -> None:
    """``invalidate_cache`` drops cached entries so the next call re-fetches."""
    svc = _tree()
    mock_core = AsyncMock(return_value=_walk_snapshot())

    with patch(_PATCH_TARGET, mock_core):
        await svc.resolve_visible_file_paths_async()
        svc.invalidate_cache()
        await svc.resolve_visible_file_paths_async()

    assert mock_core.await_count == 2


@pytest.mark.asyncio
async def test_AI_cache_drops_failed_task_so_next_call_retries() -> None:
    """A failed fetch must not stick in the cache and poison later callers."""
    svc = _tree()

    calls = 0

    async def flaky_core(**_kwargs: object) -> FolderWalkSnapshot:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return _walk_snapshot()

    with patch(_PATCH_TARGET, side_effect=flaky_core):
        with pytest.raises(RuntimeError, match="transient"):
            await svc.resolve_visible_file_paths_async()
        result = await svc.resolve_visible_file_paths_async()

    assert list(result) == []
    assert calls == 2


@pytest.mark.asyncio
async def test_AI_concurrent_cache_misses_single_flight() -> None:
    """Two concurrent misses for the same key trigger exactly one fetch."""
    import asyncio

    svc = _tree()
    call_count = 0

    async def slow_core(**_kwargs: object) -> FolderWalkSnapshot:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return _walk_snapshot()

    with patch(_PATCH_TARGET, side_effect=slow_core):
        await asyncio.gather(
            svc.resolve_visible_file_paths_async(),
            svc.resolve_visible_file_paths_async(),
            svc.resolve_visible_file_paths_async(),
        )

    assert call_count == 1


# ── Flat queries: list / filter / fuzzy search ─────────────────────────────


def _resolved_row(
    *, key: str, segments: list[str], metadata: dict | None = None
) -> tuple[ContentInfo, PurePosixPath]:
    return (_minimal_content_info(key=key, metadata=metadata), PurePosixPath(*segments))


def _patch_core(resolved: list[tuple[ContentInfo, PurePosixPath]]) -> AsyncMock:
    """Return an AsyncMock patched in for the folder-walk resolver."""
    return AsyncMock(return_value=_walk_snapshot(resolved))


@pytest.mark.asyncio
async def test_AI_list_visible_files_returns_flat_content_infos() -> None:
    """``list_visible_files_async`` drops path segments and keeps order."""
    svc = _tree()
    resolved = [
        _resolved_row(key="a.pdf", segments=["folderA", "a.pdf"]),
        _resolved_row(key="b.pdf", segments=["folderB", "b.pdf"]),
    ]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        files = await svc.list_visible_files_async()

    assert [f.key for f in files] == ["a.pdf", "b.pdf"]


@pytest.mark.asyncio
async def test_AI_filter_visible_files_applies_predicate() -> None:
    """``filter_visible_files_async`` keeps only files where the predicate is true."""
    svc = _tree()
    resolved = [
        _resolved_row(key="keep_me.pdf", segments=["x", "keep_me.pdf"]),
        _resolved_row(key="skip.pdf", segments=["x", "skip.pdf"]),
        _resolved_row(key="keep_also.pdf", segments=["y", "keep_also.pdf"]),
    ]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        kept = await svc.filter_visible_files_async(
            lambda info: info.key.startswith("keep")
        )

    assert [f.key for f in kept] == ["keep_me.pdf", "keep_also.pdf"]


@pytest.mark.asyncio
async def test_AI_filter_visible_files_reuses_cached_snapshot() -> None:
    """Multiple filter calls hit the backend exactly once thanks to the cache."""
    svc = _tree()
    resolved = [_resolved_row(key="a.pdf", segments=["a.pdf"])]
    mock_core = _patch_core(resolved)
    with patch(_PATCH_TARGET, mock_core):
        await svc.filter_visible_files_async(lambda _i: True)
        await svc.filter_visible_files_async(lambda _i: False)
        await svc.list_visible_files_async()

    assert mock_core.await_count == 1


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_ranks_by_score_and_respects_limit() -> (
    None
):
    """Results are sorted by score desc and capped at ``limit``."""
    svc = _tree()
    resolved = [
        _resolved_row(key="contract_2024.pdf", segments=["legal", "contract_2024.pdf"]),
        _resolved_row(
            key="contracts_archive.pdf",
            segments=["legal", "contracts_archive.pdf"],
        ),
        _resolved_row(key="invoice_may.pdf", segments=["finance", "invoice_may.pdf"]),
    ]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        hits = await svc.search_visible_files_fuzzy_async(
            "contract_2024", limit=2, min_score=0.0
        )

    assert len(hits) == 2
    assert hits[0].content_info.key == "contract_2024.pdf"
    assert all(isinstance(h, FuzzyMatch) for h in hits)
    assert hits == sorted(hits, key=lambda m: m.score, reverse=True)
    assert hits[0].score >= hits[1].score


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_is_case_insensitive_by_default() -> None:
    """Upper-case query matches lower-case files and vice versa by default."""
    svc = _tree()
    resolved = [
        _resolved_row(key="Annual_Report.pdf", segments=["docs", "Annual_Report.pdf"])
    ]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        hits = await svc.search_visible_files_fuzzy_async("annual_report")

    assert len(hits) == 1
    assert hits[0].content_info.key == "Annual_Report.pdf"


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_case_sensitive_opt_in() -> None:
    """With ``case_sensitive=True`` a mis-cased query is not a strong match."""
    svc = _tree()
    resolved = [_resolved_row(key="Annual_Report.pdf", segments=["Annual_Report.pdf"])]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        insensitive = await svc.search_visible_files_fuzzy_async(
            "annual_report", case_sensitive=False
        )
        sensitive = await svc.search_visible_files_fuzzy_async(
            "annual_report", case_sensitive=True, min_score=0.0
        )

    assert insensitive[0].score > sensitive[0].score


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_match_on_path_finds_folder_hits() -> None:
    """``match_on='path'`` lets folder-name queries surface their files."""
    svc = _tree()
    resolved = [
        _resolved_row(key="x.pdf", segments=["legal", "contracts_2024", "x.pdf"]),
        _resolved_row(key="y.pdf", segments=["finance", "y.pdf"]),
    ]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        hits = await svc.search_visible_files_fuzzy_async(
            "legal/contracts_2024", match_on="path", min_score=0.5
        )

    assert len(hits) == 1
    assert hits[0].content_info.key == "x.pdf"
    assert hits[0].matched_on == "path"
    assert hits[0].path == _p("legal", "contracts_2024", "x.pdf")
    assert hits[0].path.parent == _p("legal", "contracts_2024")
    assert hits[0].path.name == "x.pdf"
    assert hits[0].path_segments == ["legal", "contracts_2024", "x.pdf"]


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_matched_on_reflects_selected_target() -> (
    None
):
    """``matched_on`` must reflect what was actually scored, not a default tie.

    Regression: when ``match_on='path'`` was requested and both scores were
    ``0.0`` (e.g. a zero-similarity path), the code fell into the ``>=`` branch
    and claimed ``matched_on='key'`` even though key matching was disabled.
    """
    svc = _tree()
    resolved = [_resolved_row(key="zzz.pdf", segments=["legal", "zzz.pdf"])]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        path_hits = await svc.search_visible_files_fuzzy_async(
            "legal", match_on="path", min_score=0.0
        )
        key_hits = await svc.search_visible_files_fuzzy_async(
            "zzz", match_on="key", min_score=0.0
        )

    assert path_hits and all(h.matched_on == "path" for h in path_hits)
    assert key_hits and all(h.matched_on == "key" for h in key_hits)


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_min_score_drops_weak_matches() -> None:
    """Matches below ``min_score`` are filtered out."""
    svc = _tree()
    resolved = [
        _resolved_row(key="unrelated.pdf", segments=["unrelated.pdf"]),
    ]
    with patch(_PATCH_TARGET, _patch_core(resolved)):
        hits = await svc.search_visible_files_fuzzy_async(
            "quarterly_financials", min_score=0.8
        )

    assert hits == []


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_empty_query_returns_empty() -> None:
    """An empty query short-circuits to ``[]`` without hitting the backend."""
    svc = _tree()
    mock_core = _patch_core([])
    with patch(_PATCH_TARGET, mock_core):
        hits = await svc.search_visible_files_fuzzy_async("")

    assert hits == []
    assert mock_core.await_count == 0


@pytest.mark.asyncio
async def test_AI_search_visible_files_fuzzy_reuses_cached_snapshot() -> None:
    """Two searches with the same filter share the one cached fetch."""
    svc = _tree()
    resolved = [_resolved_row(key="a.pdf", segments=["a.pdf"])]
    mock_core = _patch_core(resolved)
    with patch(_PATCH_TARGET, mock_core):
        await svc.search_visible_files_fuzzy_async("a", min_score=0.0)
        await svc.search_visible_files_fuzzy_async("a.pdf", min_score=0.0)

    assert mock_core.await_count == 1


@pytest.mark.ai
async def test_translate_scope_id_async__returns_none__when_folder_lookup_fails() -> (
    None
):
    """A single failing folder lookup logs at debug and yields None so batch
    resolution keeps going (callers fall back to the raw scope_id)."""
    from unique_toolkit.experimental.components.content_tree.functions import (
        translate_scope_id_async,
    )

    with patch(
        "unique_toolkit.experimental.components.content_tree.deprecated.get_folder_info_async",
        new=AsyncMock(side_effect=RuntimeError("folder service unavailable")),
    ):
        resolved = await translate_scope_id_async(
            user_id="u", company_id="c", scope_id="scope_x"
        )

    assert resolved is None


_FUNCTIONS = "unique_toolkit.experimental.components.content_tree.functions"
_DEPRECATED = "unique_toolkit.experimental.components.content_tree.deprecated"


def _paginated_page(
    infos: list[ContentInfo], *, total_count: int
) -> PaginatedContentInfos:
    return PaginatedContentInfos.model_construct(
        object="list",
        content_infos=infos,
        total_count=total_count,
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_get_all_content_infos_reuses_first_page_without_count_probe() -> None:
    """
    Purpose: Listing uses the first full page's totalCount instead of a take=1 probe.
    Why this matters: The old probe discarded a round-trip and re-fetched skip=0.
    Setup summary: Two pages; assert skip=0 is requested once at step_size and skip=2 is fetched.
    """
    from unique_toolkit.experimental.components.content_tree.functions import (
        get_all_content_infos_async,
    )

    page0 = [
        _minimal_content_info(key="a.pdf", metadata=None),
        _minimal_content_info(key="b.pdf", metadata=None),
    ]
    page1 = [_minimal_content_info(key="c.pdf", metadata=None)]
    calls: list[dict[str, object]] = []

    async def fake_get_content_info(**kwargs: object) -> PaginatedContentInfos:
        calls.append(dict(kwargs))
        skip = kwargs.get("skip")
        if skip in (0, None):
            return _paginated_page(page0, total_count=3)
        return _paginated_page(page1, total_count=3)

    with patch(
        f"{_DEPRECATED}.get_content_info_async", side_effect=fake_get_content_info
    ):
        infos = await get_all_content_infos_async(
            user_id="u", company_id="c", step_size=2
        )

    assert [info.key for info in infos] == ["a.pdf", "b.pdf", "c.pdf"]
    assert len(calls) == 2
    assert calls[0]["skip"] == 0
    assert calls[0]["take"] == 2
    assert calls[1]["skip"] == 2
    assert calls[1]["take"] == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_get_all_content_infos_skips_further_fetches_when_one_page() -> None:
    """
    Purpose: A single page that covers totalCount does not issue extra requests.
    Why this matters: Small KBs must not pay for empty remaining-page gathers.
    Setup summary: First page reports total_count equal to step_size; assert one call.
    """
    from unique_toolkit.experimental.components.content_tree.functions import (
        get_all_content_infos_async,
    )

    page = [_minimal_content_info(key="only.pdf", metadata=None)]
    mock_get = AsyncMock(return_value=_paginated_page(page, total_count=1))

    with patch(f"{_DEPRECATED}.get_content_info_async", mock_get):
        infos = await get_all_content_infos_async(
            user_id="u", company_id="c", step_size=100
        )

    assert [info.key for info in infos] == ["only.pdf"]
    assert mock_get.await_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_resolve_visible_file_paths_core_looks_up_each_leaf_once() -> None:
    """
    Purpose: Path resolution calls get_folder_path once per unique leaf folder.
    Why this matters: Shared ancestors used to cost extra get_info calls.
    Setup summary: Two files under the same parent, one in a sibling; assert two path lookups.
    """
    from unique_toolkit.experimental.components.content_tree.deprecated import (
        resolve_visible_file_paths_core,
    )

    a = _minimal_content_info(
        key="a.pdf",
        metadata={"folderIdPath": "uniquepathid://root/legal"},
    )
    b = _minimal_content_info(
        key="b.pdf",
        metadata={"folderIdPath": "uniquepathid://root/legal"},
    )
    c = _minimal_content_info(
        key="c.pdf",
        metadata={"folderIdPath": "uniquepathid://root/finance"},
    )

    async def fake_path(*, scope_id: str, **_kwargs: object) -> str:
        return {
            "legal": "/Company/Legal",
            "finance": "/Company/Finance",
        }[scope_id]

    with (
        patch(
            f"{_DEPRECATED}.get_all_content_infos_async",
            AsyncMock(return_value=[a, b, c]),
        ),
        patch(
            f"{_DEPRECATED}.get_folder_path_async", side_effect=fake_path
        ) as mock_path,
    ):
        rows = await resolve_visible_file_paths_core(
            user_id="u", company_id="c", metadata_filter=None
        )

    assert mock_path.await_count == 2
    assert rows[0][1] == _p("Company", "Legal", "a.pdf")
    assert rows[1][1] == _p("Company", "Legal", "b.pdf")
    assert rows[2][1] == _p("Company", "Finance", "c.pdf")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_resolve_visible_file_paths_core_falls_back_to_raw_ids_on_path_failure() -> (
    None
):
    """
    Purpose: A failed leaf path lookup keeps raw folderIdPath segments.
    Why this matters: Partial backend failures must not drop files from the tree.
    Setup summary: get_folder_path_async raises; assert segments are the raw scope ids.
    """
    from unique_toolkit.experimental.components.content_tree.deprecated import (
        resolve_visible_file_paths_core,
    )

    info = _minimal_content_info(
        key="x.pdf",
        metadata={"folderIdPath": "uniquepathid://scope_a/scope_b"},
    )

    with (
        patch(
            f"{_DEPRECATED}.get_all_content_infos_async",
            AsyncMock(return_value=[info]),
        ),
        patch(
            f"{_DEPRECATED}.get_folder_path_async",
            AsyncMock(side_effect=RuntimeError("path unavailable")),
        ),
    ):
        rows = await resolve_visible_file_paths_core(
            user_id="u", company_id="c", metadata_filter=None
        )

    assert rows[0][1] == _p("scope_a", "scope_b", "x.pdf")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_resolve_visible_file_paths_core_uses_sentinel_without_folder_id_path() -> (
    None
):
    """
    Purpose: Content without folderIdPath still appears under the sentinel folder.
    Why this matters: Chat uploads and loose files must not be dropped.
    Setup summary: Content with empty metadata; assert _no_folder_path plus filename.
    """
    from unique_toolkit.experimental.components.content_tree.deprecated import (
        resolve_visible_file_paths_core,
    )

    info = _minimal_content_info(key="loose.txt", metadata={})

    with (
        patch(
            f"{_DEPRECATED}.get_all_content_infos_async",
            AsyncMock(return_value=[info]),
        ),
        patch(f"{_DEPRECATED}.get_folder_path_async", AsyncMock()) as mock_path,
    ):
        rows = await resolve_visible_file_paths_core(
            user_id="u", company_id="c", metadata_filter=None
        )

    assert rows[0][1] == _p("_no_folder_path", "loose.txt")
    assert mock_path.await_count == 0


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_translate_folder_path_async_returns_none_when_lookup_fails() -> None:
    """
    Purpose: A failing folder-path lookup logs at debug and yields None.
    Why this matters: Batch resolution must continue; callers fall back to raw ids.
    Setup summary: Patch get_folder_path_async to raise; assert None.
    """
    from unique_toolkit.experimental.components.content_tree.functions import (
        translate_folder_path_async,
    )

    with patch(
        f"{_DEPRECATED}.get_folder_path_async",
        AsyncMock(side_effect=RuntimeError("path unavailable")),
    ):
        resolved = await translate_folder_path_async(
            user_id="u", company_id="c", scope_id="scope_x"
        )

    assert resolved is None


# ── Folder-walk tree (Folder.get_infos + Content.get_infos) ─────────────────


def _walk_file_payload(*, key: str) -> dict[str, object]:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "id": f"id-{key}",
        "object": "content",
        "key": key,
        "byteSize": 1,
        "mimeType": "application/pdf",
        "ownerId": "owner",
        "createdAt": now,
        "updatedAt": now,
    }


def _empty_listing() -> tuple[dict[str, object], dict[str, object]]:
    return (
        {"folderInfos": [], "totalCount": 0},
        {"contentInfos": [], "totalCount": 0},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_resolves_nested_paths_from_folder_names() -> None:
    """
    Purpose: Nested files get named paths from Folder.get_infos, not get_folder_path.
    Why this matters: The folder walk must not depend on per-folder path lookups.
    Setup summary: Mock nested folder/content listings; assert path segments.
    """
    empty_folders, empty_files = _empty_listing()

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent is None:
            return {
                "folderInfos": [
                    {"id": "scope_legal", "name": "Legal", "parentId": None}
                ],
                "totalCount": 1,
            }
        if parent == "scope_legal":
            return {
                "folderInfos": [
                    {"id": "scope_q1", "name": "Q1", "parentId": "scope_legal"}
                ],
                "totalCount": 1,
            }
        if parent == "scope_q1":
            return empty_folders
        raise AssertionError(f"unexpected parentId {parent!r}")

    async def fake_content(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent is None:
            return empty_files
        if parent == "scope_legal":
            return {
                "contentInfos": [_walk_file_payload(key="a.pdf")],
                "totalCount": 1,
            }
        if parent == "scope_q1":
            return {
                "contentInfos": [_walk_file_payload(key="b.pdf")],
                "totalCount": 1,
            }
        raise AssertionError(f"unexpected parentId {parent!r}")

    with (
        patch(
            f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
            AsyncMock(side_effect=fake_folders),
        ),
        patch(
            f"{_FUNCTIONS}.unique_sdk.Content.get_infos_async",
            AsyncMock(side_effect=fake_content),
        ),
        patch(f"{_DEPRECATED}.get_folder_path_async", AsyncMock()) as mock_path,
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c"
        )

    paths = sorted(path.as_posix() for _info, path in snapshot.files)
    assert paths == [
        "Legal/Q1/b.pdf",
        "Legal/a.pdf",
    ]
    by_name = {path.name: path for _info, path in snapshot.files}
    assert by_name["a.pdf"].parent == _p("Legal")
    assert by_name["b.pdf"].parent == _p("Legal", "Q1")
    assert snapshot.complete is True
    assert mock_path.await_count == 0


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_includes_empty_folder_prefixes() -> None:
    """
    Purpose: Empty directories appear in folder_paths even with no files.
    Why this matters: Content-listing trees hide empty folders; this walk must not.
    Setup summary: Root lists one empty folder; assert extra prefix and rendered name.
    """
    empty_folders, empty_files = _empty_listing()

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent is None:
            return {
                "folderInfos": [
                    {"id": "scope_empty", "name": "Empty", "parentId": None}
                ],
                "totalCount": 1,
            }
        if parent == "scope_empty":
            return empty_folders
        raise AssertionError(f"unexpected parentId {parent!r}")

    with (
        patch(
            f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
            AsyncMock(side_effect=fake_folders),
        ),
        patch(
            f"{_FUNCTIONS}.unique_sdk.Content.get_infos_async",
            AsyncMock(return_value=empty_files),
        ),
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c"
        )

    assert snapshot.files == []
    assert _p("Empty") in snapshot.folder_paths
    assert "Empty" in snapshot.render()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_max_depth_one_does_not_list_child_directories() -> None:
    """
    Purpose: max_depth=1 lists only knowledge-base root children.
    Why this matters: Depth must reduce HTTP, unlike the content-listing renderer.
    Setup summary: Root has one folder; assert Folder.get_infos never uses its id.
    """
    empty_files = {"contentInfos": [], "totalCount": 0}

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent is None:
            return {
                "folderInfos": [
                    {"id": "scope_legal", "name": "Legal", "parentId": None}
                ],
                "totalCount": 1,
            }
        raise AssertionError(f"must not recurse into {parent!r}")

    with (
        patch(
            f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
            AsyncMock(side_effect=fake_folders),
        ) as mock_folders,
        patch(
            f"{_FUNCTIONS}.unique_sdk.Content.get_infos_async",
            AsyncMock(return_value=empty_files),
        ),
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c", max_depth=1
        )

    assert snapshot.folder_paths == [_p("Legal")]
    parent_ids = [call.kwargs.get("parentId") for call in mock_folders.await_args_list]
    assert parent_ids == [None]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_paginates_when_total_count_exceeds_take() -> None:
    """
    Purpose: Remaining folder pages are fetched when totalCount exceeds take.
    Why this matters: Directories with more than one page must not be truncated.
    Setup summary: Root folders totalCount=2 with step_size=1; assert skip 0 and 1.
    """
    all_folders = [
        {"id": "scope_a", "name": "A", "parentId": None},
        {"id": "scope_b", "name": "B", "parentId": None},
    ]
    empty_files = {"contentInfos": [], "totalCount": 0}

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        skip = int(kwargs["skip"])  # type: ignore[arg-type]
        take = int(kwargs["take"])  # type: ignore[arg-type]
        if parent is None:
            page = all_folders[skip : skip + take]
            return {"folderInfos": page, "totalCount": 2}
        return {"folderInfos": [], "totalCount": 0}

    with (
        patch(
            f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
            AsyncMock(side_effect=fake_folders),
        ) as mock_folders,
        patch(
            f"{_FUNCTIONS}.unique_sdk.Content.get_infos_async",
            AsyncMock(return_value=empty_files),
        ),
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c", max_depth=1, step_size=1
        )

    root_skips = sorted(
        call.kwargs["skip"]
        for call in mock_folders.await_args_list
        if call.kwargs.get("parentId") is None
    )
    assert root_skips == [0, 1]
    assert sorted(snapshot.folder_paths) == [_p("A"), _p("B")]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_folder_walk_resolve_is_cached_across_calls() -> None:
    """
    Purpose: A second folder-walk with the same args reuses the cached task.
    Why this matters: Repeat renders must not re-walk the knowledge base.
    Setup summary: Patch walk helper; call resolve twice; assert one backend call.
    """
    from unique_toolkit.experimental.components.content_tree.schemas import (
        FolderWalkSnapshot,
    )

    svc = _tree()
    snapshot = FolderWalkSnapshot(files=[], folder_paths=[_p("Legal")])
    mock_walk = AsyncMock(return_value=snapshot)
    with patch(_WALK_PATCH, mock_walk):
        first = await svc.resolve_visible_file_paths_via_folders_async(max_depth=2)
        second = await svc.resolve_visible_file_paths_via_folders_async(max_depth=2)

    assert first is second
    assert mock_walk.await_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_folder_walk_cache_keys_on_max_depth() -> None:
    """
    Purpose: Different max_depth values do not share a cached walk.
    Why this matters: Depth limits which directories are fetched.
    Setup summary: Call resolve with max_depth 1 then 2; assert two walk calls.
    """
    from unique_toolkit.experimental.components.content_tree.schemas import (
        FolderWalkSnapshot,
    )

    svc = _tree()
    mock_walk = AsyncMock(return_value=FolderWalkSnapshot(files=[], folder_paths=[]))
    with patch(_WALK_PATCH, mock_walk):
        await svc.resolve_visible_file_paths_via_folders_async(max_depth=1)
        await svc.resolve_visible_file_paths_via_folders_async(max_depth=2)

    assert mock_walk.await_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_render_visible_tree_async_includes_empty_dirs() -> None:
    """
    Purpose: Public tree renderer draws empty folders from the folder walk.
    Why this matters: render_visible_tree_async must use depth-based listing, not content dump.
    Setup summary: Stub a snapshot with only folder_paths; assert name in output.
    """
    from unique_toolkit.experimental.components.content_tree.schemas import (
        FolderWalkSnapshot,
    )

    svc = _tree()
    snapshot = FolderWalkSnapshot(files=[], folder_paths=[_p("Archive")])
    with patch(_WALK_PATCH, AsyncMock(return_value=snapshot)):
        rendered = await svc.render_visible_tree_async()

    assert "Archive" in rendered


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_folder_walk_failed_task_is_dropped_from_cache() -> None:
    """
    Purpose: A failed folder walk is not cached so the next call retries.
    Why this matters: Transient listing errors must not poison later renders.
    Setup summary: First walk raises; second succeeds; assert two calls.
    """
    from unique_toolkit.experimental.components.content_tree.schemas import (
        FolderWalkSnapshot,
    )

    svc = _tree()
    calls = 0

    async def flaky_walk(**_kwargs: object) -> FolderWalkSnapshot:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return FolderWalkSnapshot(files=[], folder_paths=[])

    with patch(_WALK_PATCH, side_effect=flaky_walk):
        with pytest.raises(RuntimeError, match="transient"):
            await svc.resolve_visible_file_paths_via_folders_async()
        result = await svc.resolve_visible_file_paths_via_folders_async()

    assert result.files == []
    assert calls == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_timeout_returns_partial_snapshot() -> None:
    """
    Purpose: A walk timeout returns listed directories instead of raising.
    Why this matters: Callers can evaluate a partial tree without failing the run.
    Setup summary: Root lists instantly; child listing sleeps; timeout before child.
    """
    empty_files = {"contentInfos": [], "totalCount": 0}

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent is None:
            return {
                "folderInfos": [
                    {"id": "scope_legal", "name": "Legal", "parentId": None}
                ],
                "totalCount": 1,
            }
        await asyncio.sleep(0.5)
        return {"folderInfos": [], "totalCount": 0}

    with (
        patch(
            f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
            AsyncMock(side_effect=fake_folders),
        ),
        patch(
            f"{_FUNCTIONS}.unique_sdk.Content.get_infos_async",
            AsyncMock(return_value=empty_files),
        ),
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c", timeout=0.05
        )

    assert snapshot.complete is False
    assert snapshot.folder_paths == [_p("Legal")]
    assert snapshot.files == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_skips_unscoped_content_listing_at_root() -> None:
    """
    Purpose: Root listing does not call Content.get_infos without parentId.
    Why this matters: That endpoint dumps every visible file and stalled timeouts at 0 rows.
    Setup summary: Walk one root folder; assert every content call has parentId.
    """
    content_parent_ids: list[object] = []

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        if parent is None:
            return {
                "folderInfos": [
                    {"id": "scope_legal", "name": "Legal", "parentId": None}
                ],
                "totalCount": 1,
            }
        return {"folderInfos": [], "totalCount": 0}

    async def fake_content(**kwargs: object) -> dict[str, object]:
        content_parent_ids.append(kwargs.get("parentId"))
        return {"contentInfos": [], "totalCount": 0}

    with (
        patch(
            f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
            AsyncMock(side_effect=fake_folders),
        ),
        patch(
            f"{_FUNCTIONS}.unique_sdk.Content.get_infos_async",
            AsyncMock(side_effect=fake_content),
        ),
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c", max_depth=2
        )

    assert snapshot.folder_paths == [_p("Legal")]
    assert content_parent_ids == ["scope_legal"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_walk_timeout_keeps_first_folder_page() -> None:
    """
    Purpose: A timeout after the first folder page still returns those folders.
    Why this matters: Partial trees must not wait for every remaining page.
    Setup summary: Root totalCount=2, step_size=1; second page sleeps past timeout.
    """

    async def fake_folders(**kwargs: object) -> dict[str, object]:
        parent = kwargs.get("parentId")
        skip = int(kwargs["skip"])  # type: ignore[arg-type]
        if parent is None and skip == 0:
            return {
                "folderInfos": [{"id": "scope_a", "name": "A", "parentId": None}],
                "totalCount": 2,
            }
        if parent is None:
            await asyncio.sleep(0.5)
            return {
                "folderInfos": [{"id": "scope_b", "name": "B", "parentId": None}],
                "totalCount": 2,
            }
        return {"folderInfos": [], "totalCount": 0}

    with patch(
        f"{_FUNCTIONS}.unique_sdk.Folder.get_infos_async",
        AsyncMock(side_effect=fake_folders),
    ):
        snapshot = await walk_visible_paths_via_folders_async(
            user_id="u", company_id="c", max_depth=1, step_size=1, timeout=0.05
        )

    assert snapshot.complete is False
    assert _p("A") in snapshot.folder_paths
    assert _p("B") not in snapshot.folder_paths


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_service_timeout_returns_partial_and_fills_cache() -> None:
    """
    Purpose: Service timeout returns a partial copy while the cached walk continues.
    Why this matters: Higher layers can evaluate now and later await the full tree.
    Setup summary: Walk records one folder, waits on an event, then records a child.
    """
    svc = _tree()
    released = asyncio.Event()

    async def slow_walk(
        *_args: object,
        progress: FolderWalkSnapshot | None = None,
        **_kwargs: object,
    ) -> FolderWalkSnapshot:
        acc = progress or FolderWalkSnapshot(files=[], folder_paths=[], complete=False)
        acc.folder_paths.append(_p("Legal"))
        await released.wait()
        acc.folder_paths.append(_p("Legal", "Q1"))
        acc.complete = True
        return acc.copy(complete=True)

    with patch(_WALK_PATCH, side_effect=slow_walk) as mock_walk:
        partial = await svc.resolve_visible_file_paths_via_folders_async(timeout=0.2)
        assert partial.complete is False
        assert partial.folder_paths == [_p("Legal")]
        released.set()
        full = await svc.resolve_visible_file_paths_via_folders_async()

    assert full.complete is True
    assert full.folder_paths == [_p("Legal"), _p("Legal", "Q1")]
    assert mock_walk.await_count == 1
    assert partial.folder_paths == [_p("Legal")]
