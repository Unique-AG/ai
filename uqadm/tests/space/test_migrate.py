"""Tests for ``uqadm space migrate`` module-level helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.migrate import build_module_updates_from_pairs, cmd_migrate


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


# --- cmd_migrate integration (with mocks) ---


@patch("uqadm.space.migrate.Space.get_space")
@patch("uqadm.core.cli_auth.config_for_slot")
def test_cmd_migrate_dry_run_create_loads_both_slots(
    mock_cfg: MagicMock,
    mock_get: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run create migration loads source and destination slots then stops."""
    mock_cfg.side_effect = [
        MagicMock(user_id="us", company_id="c1", api_base="https://api.example"),
        MagicMock(user_id="ud", company_id="c1", api_base="https://api.example"),
    ]
    mock_get.return_value = {"name": "S", "fallbackModule": "m", "modules": []}

    cmd_migrate(
        "src:space_a",
        "dst",
        dry_run=True,
        with_knowledge=False,
        cwd=None,
    )

    out = capsys.readouterr().out
    assert "Loading source slot 'src'" in out
    assert "Loading destination slot 'dst'" in out
    assert "Dry-run: would create_space" in out
    assert mock_cfg.call_count == 2
