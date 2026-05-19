"""Tests for auth-failure heuristics and credential debug formatting."""

from __future__ import annotations

from unique_sdk import AuthenticationError
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import (
    format_credential_debug_lines,
    is_likely_auth_failure,
)


def test_is_likely_auth_failure_authentication_error() -> None:
    assert is_likely_auth_failure(AuthenticationError("nope", http_status=401))


def test_is_likely_auth_failure_http_status_attr() -> None:
    class E(Exception):
        http_status = 401

    assert is_likely_auth_failure(E("x"))


def test_is_likely_auth_failure_message_unauthorized() -> None:
    assert is_likely_auth_failure(RuntimeError("Unauthorized: bad token"))


def test_is_likely_auth_failure_other() -> None:
    assert not is_likely_auth_failure(RuntimeError("connection reset"))


def test_format_credential_debug_lines_redacts_long_key() -> None:
    raw_key = "ukey_" + "a" * 20 + "ZZZZ"
    cfg = Config(
        user_id="user_1",
        company_id="co_1",
        api_key=raw_key,
        app_id="",
        api_base="https://gw.example/base",
    )
    lines = format_credential_debug_lines(cfg, label="test", exc=None)
    text = "\n".join(lines)
    assert "user_1" in text
    assert "co_1" in text
    assert raw_key not in text
    assert "ZZZZ" not in text
    assert "ukey_" not in text
    assert f"length {len(raw_key)}" in text
    assert "redacted" in text


def test_format_credential_debug_lines_short_key_redacted() -> None:
    cfg = Config(
        user_id="user_1",
        company_id="co_1",
        api_key="abc123",
        app_id="",
        api_base="https://gw.example/base",
    )
    lines = format_credential_debug_lines(cfg, label="test", exc=None)
    text = "\n".join(lines)
    assert "abc123" not in text
    assert "length 6" in text
    assert "redacted" in text


def test_format_credential_debug_lines_empty_key() -> None:
    cfg = Config(
        user_id="user_1",
        company_id="co_1",
        api_key="",
        app_id="",
        api_base="https://gw.example/base",
    )
    lines = format_credential_debug_lines(cfg, label="test", exc=None)
    text = "\n".join(lines)
    assert "empty" in text
    assert "length" not in text.split("UNIQUE_API_KEY:")[1]
