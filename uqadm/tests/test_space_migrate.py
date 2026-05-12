"""Tests for ``uqadm space_migrate`` module-level helpers."""

from __future__ import annotations

from typing import Any

from uqadm.space_migrate import build_module_updates_from_pairs


def test_build_module_updates_from_pairs_returns_destination_module_id() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        ({"name": "alpha"}, {"id": "mod_dst_1", "name": "alpha"}),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [{"moduleId": "mod_dst_1", "name": "alpha"}]


def test_build_module_updates_from_pairs_includes_present_optional_fields() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            {
                "name": "alpha",
                "description": "desc",
                "weight": 3,
                "configuration": {"k": "v"},
            },
            {"id": "mod_dst_1", "name": "alpha-dst"},
        ),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [
        {
            "moduleId": "mod_dst_1",
            "name": "alpha",
            "description": "desc",
            "weight": 3,
            "configuration": {"k": "v"},
        }
    ]


def test_build_module_updates_from_pairs_skips_none_optional_fields() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            {
                "name": "alpha",
                "description": None,
                "weight": None,
                "configuration": None,
            },
            {"id": "mod_dst_1"},
        ),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [{"moduleId": "mod_dst_1", "name": "alpha"}]


def test_build_module_updates_from_pairs_handles_multiple_entries() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        ({"name": "a"}, {"id": "1"}),
        ({"name": "b", "weight": 7}, {"id": "2"}),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [
        {"moduleId": "1", "name": "a"},
        {"moduleId": "2", "name": "b", "weight": 7},
    ]


def test_build_module_updates_from_pairs_empty() -> None:
    assert build_module_updates_from_pairs([]) == []
