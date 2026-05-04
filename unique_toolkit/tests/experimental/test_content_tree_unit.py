"""Unit tests for :class:`~unique_toolkit.experimental.components.content_tree.service.ContentTree`."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.experimental.content_tree import (
    ContentTree,
    FuzzyMatch,
    extract_scope_ids_from_content_infos,
    format_path_trie,
)

# All patches target the name as bound in ``experimental.components.content_tree.service``
# (where the service module imports it from ``functions``), not the original
# definition module. That's the usual ``mock.patch`` rule: patch where it's
# looked up.
_PATCH_TARGET = "unique_toolkit.experimental.components.content_tree.service.resolve_visible_file_paths_core"


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


def test_AI_build_trie_groups_path_segments() -> None:
    """Building a trie merges files under the correct folder chain."""
    resolved = [
        (
            _minimal_content_info(
                key="a.pdf",
                metadata={"folderIdPath": "uniquepathid://s1/s2"},
            ),
            ["Scope1", "Scope2", "a.pdf"],
        ),
        (
            _minimal_content_info(
                key="b.pdf",
                metadata={"folderIdPath": "uniquepathid://s1/s2"},
            ),
            ["Scope1", "Scope2", "b.pdf"],
        ),
    ]
    trie = ContentTree.build_trie_from_resolved_paths(resolved)
    assert sorted(trie.children["Scope1"].children["Scope2"].files) == [
        "a.pdf",
        "b.pdf",
    ]


def test_AI_format_path_trie_truncates_at_max_depth() -> None:
    """Depth-limited rendering omits deeper files (``tree -L`` semantics)."""
    trie = ContentTree.build_trie_from_resolved_paths(
        [
            (
                _minimal_content_info(key="deep.pdf", metadata=None),
                ["top", "mid", "deep.pdf"],
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
                ["top", "mid", "a.pdf"],
            ),
            (
                _minimal_content_info(key="b.pdf", metadata=None),
                ["top", "mid", "b.pdf"],
            ),
            (
                _minimal_content_info(key="c.pdf", metadata=None),
                ["top", "other", "nested", "c.pdf"],
            ),
        ]
    )
    out = format_path_trie(trie, max_depth=1)
    # Below ``top``: 3 dirs (mid, other, nested) and 3 files (a.pdf, b.pdf, c.pdf).
    assert "(3 dirs, 3 files below)" in out


def test_AI_extract_scope_ids_matches_folder_id_path() -> None:
    """Scope id extraction strips the ``uniquepathid://`` prefix."""
    infos = [
        _minimal_content_info(
            key="x",
            metadata={"folderIdPath": "uniquepathid://aa/bb"},
        ),
    ]
    assert extract_scope_ids_from_content_infos(infos) == {"aa", "bb"}


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
            ["_no_folder_path", "a.pdf"],
        ),
    ]

    mock_core = AsyncMock(return_value=resolved)
    with patch(_PATCH_TARGET, mock_core):
        first = await svc.resolve_visible_file_paths_async()
        second = await svc.resolve_visible_file_paths_async()

    assert first is second
    assert mock_core.await_count == 1


@pytest.mark.asyncio
async def test_AI_cache_keys_on_effective_metadata_filter() -> None:
    """Different effective filters must not collide in the cache."""
    svc = _tree(metadata_filter={"env": "prod"})

    mock_core = AsyncMock(
        side_effect=lambda **kw: [
            (
                _minimal_content_info(
                    key=f"for-{(kw.get('metadata_filter') or {}).get('env', 'none')}.pdf",
                    metadata=None,
                ),
                ["_no_folder_path", "x.pdf"],
            )
        ]
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
    mock_core = AsyncMock(return_value=[])

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

    async def flaky_core(**_kwargs: object) -> list:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return []

    with patch(_PATCH_TARGET, side_effect=flaky_core):
        with pytest.raises(RuntimeError, match="transient"):
            await svc.resolve_visible_file_paths_async()
        result = await svc.resolve_visible_file_paths_async()

    assert result == []
    assert calls == 2


@pytest.mark.asyncio
async def test_AI_concurrent_cache_misses_single_flight() -> None:
    """Two concurrent misses for the same key trigger exactly one fetch."""
    import asyncio

    svc = _tree()
    call_count = 0

    async def slow_core(**_kwargs: object) -> list:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return []

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
) -> tuple[ContentInfo, list[str]]:
    return (_minimal_content_info(key=key, metadata=metadata), segments)


def _patch_core(resolved: list[tuple[ContentInfo, list[str]]]) -> AsyncMock:
    """Return an AsyncMock patched in for the core resolver."""
    mock_core = AsyncMock(return_value=resolved)
    return mock_core


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
