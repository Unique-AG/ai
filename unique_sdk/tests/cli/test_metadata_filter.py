"""Tests for unique_sdk.cli.metadata_filter.

These exercise the UniqueQL filter-tree evaluator in isolation: the two
API-backed lookups (scope_id -> path, content_id -> owner path) are replaced
with in-memory stubs, so no ShellState/unique_sdk mocking is needed. See
UN-21780.
"""

from __future__ import annotations

from typing import Any

from unique_sdk.cli.metadata_filter import MetadataFilter


def _make_filter(
    tree: dict[str, Any],
    *,
    scope_paths: dict[str, str] | None = None,
    owner_paths: dict[str, str] | None = None,
) -> tuple[MetadataFilter, dict[str, int]]:
    """Build a MetadataFilter over in-memory stubs.

    Returns the filter and a ``{"scope": n, "owner": n}`` call counter so tests
    can assert the per-content verdict cache avoids repeated owner lookups.
    """
    scope_paths = scope_paths or {}
    owner_paths = owner_paths or {}
    calls = {"scope": 0, "owner": 0}

    def resolve_scope_path(scope_id: str) -> str | None:
        calls["scope"] += 1
        return scope_paths.get(scope_id)

    def resolve_content_owner_path(content_id: str) -> str | None:
        calls["owner"] += 1
        return owner_paths.get(content_id)

    mf = MetadataFilter(
        tree,
        resolve_scope_path=resolve_scope_path,
        resolve_content_owner_path=resolve_content_owner_path,
    )
    return mf, calls


class TestAllowsContent:
    def test_contentid_membership_allows_and_denies(self) -> None:
        mf, _ = _make_filter(
            {"path": ["contentId"], "operator": "in", "value": ["cont_a", "cont_b"]}
        )
        assert mf.allows_content("cont_a")
        assert mf.allows_content("cont_b")
        assert not mf.allows_content("cont_c")

    def test_negated_contentid_inverts(self) -> None:
        mf, _ = _make_filter(
            {"path": ["contentId"], "operator": "notIn", "value": ["cont_x"]}
        )
        assert not mf.allows_content("cont_x")
        assert mf.allows_content("cont_other")

    def test_negated_overlaps_contentid_inverts(self) -> None:
        mf, _ = _make_filter(
            {"path": ["contentId"], "operator": "notOverlaps", "value": ["cont_x"]}
        )
        assert not mf.allows_content("cont_x")
        assert mf.allows_content("cont_other")

    def test_folder_containment(self) -> None:
        mf, _ = _make_filter(
            {"path": ["folderIdPath"], "operator": "contains", "value": "scope_fund_a"},
            scope_paths={"scope_fund_a": "/Funds/Fund A"},
            owner_paths={
                "cont_in": "/Funds/Fund A/Sub",
                "cont_out": "/Funds/Fund B",
            },
        )
        assert mf.allows_content("cont_in")
        assert not mf.allows_content("cont_out")

    def test_unknown_owner_fails_closed(self) -> None:
        mf, _ = _make_filter(
            {"path": ["folderIdPath"], "operator": "contains", "value": "scope_a"},
            scope_paths={"scope_a": "/A"},
        )
        assert not mf.allows_content("cont_unresolved")

    def test_non_boundary_leaf_fails_closed(self) -> None:
        mf, _ = _make_filter(
            {"path": ["mimeType"], "operator": "equals", "value": "application/pdf"}
        )
        assert not mf.allows_content("cont_a")

    def test_or_short_circuits_to_contentid_without_owner_lookup(self) -> None:
        mf, calls = _make_filter(
            {
                "or": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {"path": ["contentId"], "operator": "in", "value": ["cont_a"]},
                ]
            },
            scope_paths={"scope_a": "/A"},
        )
        assert mf.allows_content("cont_a")
        # contentId leaf is sorted first and short-circuits, so the folder
        # branch never resolves the owner path.
        assert calls["owner"] == 0

    def test_and_excludes_contentid_outside_required_folder(self) -> None:
        mf, _ = _make_filter(
            {
                "and": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {"path": ["contentId"], "operator": "in", "value": ["cont_a"]},
                ]
            },
            scope_paths={"scope_a": "/A"},
            owner_paths={"cont_a": "/B"},  # listed but lives outside /A
        )
        assert not mf.allows_content("cont_a")

    def test_verdict_is_cached(self) -> None:
        mf, calls = _make_filter(
            {"path": ["folderIdPath"], "operator": "contains", "value": "scope_a"},
            scope_paths={"scope_a": "/A"},
            owner_paths={"cont_a": "/A/x"},
        )
        assert mf.allows_content("cont_a")
        assert mf.allows_content("cont_a")
        assert calls["owner"] == 1  # second call served from the verdict cache

    def test_empty_and_or_fail_closed(self) -> None:
        assert not _make_filter({"and": []})[0].allows_content("cont_a")
        assert not _make_filter({"or": []})[0].allows_content("cont_a")

    def test_non_dict_node_fails_closed(self) -> None:
        mf, _ = _make_filter({"and": ["not-a-dict"]})
        assert not mf.allows_content("cont_a")


class TestFolderNavigation:
    def test_navigable_ids_exclude_or_with_contentid(self) -> None:
        mf, _ = _make_filter(
            {
                "and": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {
                        "or": [
                            {
                                "path": ["folderIdPath"],
                                "operator": "contains",
                                "value": "scope_b",
                            },
                            {
                                "path": ["contentId"],
                                "operator": "in",
                                "value": ["cont_x"],
                            },
                        ]
                    },
                ]
            }
        )
        # scope_a is on the conjunctive spine; scope_b is only an OR-alternative
        # to a contentId allowlist, so it is not standalone-navigable.
        assert mf.navigable_folder_ids() == ["scope_a"]

    def test_allows_folder_scope_containment(self) -> None:
        mf, _ = _make_filter(
            {"path": ["folderIdPath"], "operator": "contains", "value": "scope_a"},
            scope_paths={"scope_a": "/A", "scope_sub": "/A/Sub", "scope_x": "/X"},
        )
        assert mf.allows_folder_scope("scope_sub")
        assert not mf.allows_folder_scope("scope_x")

    def test_allows_folder_path_blocks_dotdot_escape(self) -> None:
        mf, _ = _make_filter(
            {"path": ["folderIdPath"], "operator": "contains", "value": "scope_a"},
            scope_paths={"scope_a": "/A"},
        )
        assert mf.allows_folder_path("/A/new")
        assert not mf.allows_folder_path("/A/../Other")

    def test_scope_resolves_paths_and_returns_content_ids(self) -> None:
        mf, _ = _make_filter(
            {
                "and": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {"path": ["contentId"], "operator": "in", "value": ["cont_x"]},
                ]
            },
            scope_paths={"scope_a": "/A"},
        )
        folders, content_ids = mf.scope()
        assert folders == ["/A"]
        assert content_ids == ["cont_x"]


class TestDescribeNavigableScope:
    """``describe_navigable_scope`` classifies content ids as folder-restricted
    vs free for precise denial hints (UN-21780)."""

    def test_pure_content_ids_are_free(self) -> None:
        mf, _ = _make_filter(
            {"path": ["contentId"], "operator": "in", "value": ["cont_x", "cont_y"]}
        )
        folders, free, restricted = mf.describe_navigable_scope()
        assert folders == []
        assert free == ["cont_x", "cont_y"]
        assert restricted == []

    def test_and_combined_content_ids_are_folder_restricted(self) -> None:
        mf, _ = _make_filter(
            {
                "and": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {
                        "path": ["contentId"],
                        "operator": "in",
                        "value": ["cont_x", "cont_y"],
                    },
                ]
            },
            scope_paths={"scope_a": "/A"},
        )
        folders, free, restricted = mf.describe_navigable_scope()
        assert folders == ["/A"]
        assert free == []
        # Reachable only *within* /A — must not be advertised as freely readable.
        assert restricted == ["cont_x", "cont_y"]

    def test_or_alternative_content_id_is_free(self) -> None:
        mf, _ = _make_filter(
            {
                "or": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {"path": ["contentId"], "operator": "in", "value": ["cont_x"]},
                ]
            },
            scope_paths={"scope_a": "/A"},
        )
        folders, free, restricted = mf.describe_navigable_scope()
        # The OR mixes a folder grant with a contentId allowlist, so the folder
        # is not standalone-navigable; the content id is reachable on its own.
        assert folders == []
        assert free == ["cont_x"]
        assert restricted == []

    def test_nested_or_under_and_is_folder_restricted(self) -> None:
        mf, _ = _make_filter(
            {
                "and": [
                    {
                        "path": ["folderIdPath"],
                        "operator": "contains",
                        "value": "scope_a",
                    },
                    {
                        "or": [
                            {
                                "path": ["folderIdPath"],
                                "operator": "contains",
                                "value": "scope_b",
                            },
                            {
                                "path": ["contentId"],
                                "operator": "in",
                                "value": ["cont_x"],
                            },
                        ]
                    },
                ]
            },
            scope_paths={"scope_a": "/A", "scope_b": "/B"},
        )
        folders, free, restricted = mf.describe_navigable_scope()
        # /A is on the conjunctive spine; /B is only an OR alternative.
        assert folders == ["/A"]
        assert free == []
        # cont_x must additionally live under /A, so it is folder-restricted.
        assert restricted == ["cont_x"]
