"""Unit tests for ``unique_toolkit._common.metadata_filter_scope``."""

from __future__ import annotations

import pytest

from unique_toolkit._common.metadata_filter_scope import (
    build_folder_id_in_clause,
    merge_scope_clause_into_metadata_filter,
)


@pytest.mark.ai
def test_build_folder_id_in_clause__rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        build_folder_id_in_clause([])


@pytest.mark.ai
def test_build_folder_id_in_clause__single() -> None:
    assert build_folder_id_in_clause(["scope-1"]) == {
        "path": ["folderId"],
        "operator": "in",
        "value": ["scope-1"],
    }


@pytest.mark.ai
def test_build_folder_id_in_clause__multi() -> None:
    assert build_folder_id_in_clause(["scope-1", "scope-2"]) == {
        "path": ["folderId"],
        "operator": "in",
        "value": ["scope-1", "scope-2"],
    }


@pytest.mark.ai
def test_and_merge__flattens_top_level_and() -> None:
    scope = build_folder_id_in_clause(["scope-x"])
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
    scope = build_folder_id_in_clause(["scope-x"])
    existing = {"path": ["dept"], "operator": "equals", "value": "Legal"}
    merged = merge_scope_clause_into_metadata_filter(scope, existing)
    assert merged == {"and": [scope, existing]}


@pytest.mark.ai
def test_and_merge__returns_scope_when_no_existing_filter() -> None:
    scope = build_folder_id_in_clause(["scope-x"])
    assert merge_scope_clause_into_metadata_filter(scope, None) == scope
