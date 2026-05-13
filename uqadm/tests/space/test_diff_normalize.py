"""Tests for space diff normalization and helpers."""

from __future__ import annotations

from uqadm.space.diff import _normalize_for_diff


def test_normalize_strips_ephemeral_keys_recursively() -> None:
    payload = {
        "id": "space_1",
        "moduleId": "mod_x",
        "createdAt": "t1",
        "companyId": "c1",
        "nested": {"createdAt": "x", "name": "n", "id": "inner"},
        "items": [{"updatedAt": "u", "moduleId": "m", "v": 1}],
        "keep": True,
    }
    out = _normalize_for_diff(payload, strict=False)
    assert out["keep"] is True
    assert "id" not in out
    assert "moduleId" not in out
    assert "createdAt" not in out
    assert "companyId" not in out
    assert "createdAt" not in out["nested"]
    assert "id" not in out["nested"]
    assert out["nested"]["name"] == "n"
    assert "updatedAt" not in out["items"][0]
    assert "moduleId" not in out["items"][0]
    assert out["items"][0]["v"] == 1


def test_normalize_strict_preserves_ephemeral_keys() -> None:
    payload = {"id": "x", "createdAt": "t"}
    assert _normalize_for_diff(payload, strict=True) == payload


def test_non_strict_normalize_strips_id() -> None:
    assert _normalize_for_diff({"id": 1, "a": 2}, strict=False) == {"a": 2}


def test_normalize_non_container() -> None:
    assert _normalize_for_diff("x", strict=False) == "x"
    assert _normalize_for_diff(None, strict=False) is None
