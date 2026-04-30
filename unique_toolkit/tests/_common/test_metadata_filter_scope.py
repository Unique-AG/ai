"""Unit tests for ``unique_toolkit._common.metadata_filter_scope``."""

from __future__ import annotations

import warnings

import pytest

from unique_toolkit._common.metadata_filter_scope import (
    build_folder_id_scope_clause,
    merge_deprecated_scope_ids_into_filter,
    merge_scope_clause_into_metadata_filter,
)


@pytest.mark.ai
def test_build_folder_id_scope_clause__single_and_multi() -> None:
    assert build_folder_id_scope_clause(["a"]) == {
        "path": ["folderId"],
        "operator": "in",
        "value": ["a"],
    }
    assert build_folder_id_scope_clause(["a", "b"])["value"] == ["a", "b"]


@pytest.mark.ai
def test_and_merge__flattens_top_level_and() -> None:
    scope = build_folder_id_scope_clause(["x"])
    existing = {"and": [{"path": ["year"], "operator": "equals", "value": "2024"}]}
    merged = merge_scope_clause_into_metadata_filter(scope, existing)
    assert merged == {
        "and": [
            scope,
            {"path": ["year"], "operator": "equals", "value": "2024"},
        ]
    }


@pytest.mark.ai
def test_and_merge__wraps_non_and_filter() -> None:
    scope = build_folder_id_scope_clause(["x"])
    existing = {"path": ["dept"], "operator": "equals", "value": "Legal"}
    merged = merge_scope_clause_into_metadata_filter(scope, existing)
    assert merged == {"and": [scope, existing]}


@pytest.mark.ai
def test_merge_deprecated_scope_ids_into_filter__warns_and_merges() -> None:
    with pytest.warns(DeprecationWarning, match="deprecated"):
        out = merge_deprecated_scope_ids_into_filter(
            ["s1"],
            {"path": ["t"], "operator": "equals", "value": "v"},
            deprecation_message="scope_ids is deprecated",
        )
    assert out == {
        "and": [
            build_folder_id_scope_clause(["s1"]),
            {"path": ["t"], "operator": "equals", "value": "v"},
        ]
    }


@pytest.mark.ai
def test_merge_deprecated_scope_ids_into_filter__empty_scope_no_warning() -> None:
    with warnings.catch_warnings(record=True) as record:
        out = merge_deprecated_scope_ids_into_filter(
            [],
            {"a": 1},
            deprecation_message="should not warn",
        )
    assert out == {"a": 1}
    assert not record
