"""Tests for diff timestamp stripping."""

from __future__ import annotations

from uqadm.space_diff import _strip_volatile


def test_strip_volatile_removes_timestamp_keys() -> None:
    payload = {
        "id": "space_1",
        "createdAt": "t1",
        "nested": {"createdAt": "x", "name": "n"},
        "items": [{"updatedAt": "u", "v": 1}],
    }
    out = _strip_volatile(payload)
    assert out["id"] == "space_1"
    assert "createdAt" not in out
    assert "createdAt" not in out["nested"]
    assert out["nested"]["name"] == "n"
    assert "updatedAt" not in out["items"][0]
    assert out["items"][0]["v"] == 1


def test_strip_volatile_non_container() -> None:
    assert _strip_volatile("x") == "x"
    assert _strip_volatile(None) is None
