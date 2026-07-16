"""Tests for slot resolution, including UQADM_AUTH_FROM_ENV behavior."""

from __future__ import annotations

import pytest

from uqadm.core.slot import MissingDefaultSlotError, resolve_slot


def test_resolve_slot_explicit_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UQADM_AUTH_FROM_ENV", raising=False)
    assert resolve_slot("prod") == "prod"


def test_resolve_slot_env_auth_returns_label_without_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With env-auth on and no slot given, resolve_slot yields the 'env' label."""
    monkeypatch.setenv("UQADM_AUTH_FROM_ENV", "1")
    assert resolve_slot(None) == "env"


def test_resolve_slot_explicit_still_wins_under_env_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UQADM_AUTH_FROM_ENV", "1")
    assert resolve_slot("prod") == "prod"


def test_resolve_slot_no_slot_no_default_no_env_auth_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("UQADM_AUTH_FROM_ENV", raising=False)
    monkeypatch.setattr("uqadm.core.slot.get_default_slot", lambda: None)
    with pytest.raises(MissingDefaultSlotError):
        resolve_slot(None)
