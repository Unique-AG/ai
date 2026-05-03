"""Tests for unique_sdk.cli.config."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest

import unique_sdk
from unique_sdk.cli.config import Config, load_config

# Stable fake gateway root for UNIQUE_API_BASE tests (not a real hostname).
_TEST_PUBLIC_CHAT_BASE = "https://test-api-base.example/public/chat-gen2"


@pytest.fixture(autouse=True)
def _reset_sdk_ingestion_setting() -> Generator[None, None, None]:
    """Snapshot/restore ``unique_sdk.ingestion_upload_api_url_internal``
    around every CLI config test.

    ``load_config`` writes onto the SDK module global as a side effect
    (same shape as ``unique_sdk.api_key`` / ``api_base`` /``app_id``).
    Without a per-test reset, a test that exercises the env-var path
    would leak its value into sibling tests that expect the global to
    start at ``None``, producing order-dependent failures.
    """
    original = unique_sdk.ingestion_upload_api_url_internal
    try:
        unique_sdk.ingestion_upload_api_url_internal = None
        yield
    finally:
        unique_sdk.ingestion_upload_api_url_internal = original


class TestConfig:
    def test_config_stores_values(self) -> None:
        c = Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
        assert c.user_id == "u1"
        assert c.company_id == "c1"
        assert c.api_key == "key"
        assert c.app_id == "app"
        assert c.api_base == "https://example.com"
        # Default for the new field — kwarg is optional and falls back
        # to ``None`` so existing call sites that build a ``Config``
        # without it continue to compile.
        assert c.ingestion_upload_api_url_internal is None

    def test_config_stores_ingestion_upload_url(self) -> None:
        c = Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
            ingestion_upload_api_url_internal=(
                "http://node-ingestion.test.svc.cluster.local:8091/scoped/upload"
            ),
        )
        assert c.ingestion_upload_api_url_internal == (
            "http://node-ingestion.test.svc.cluster.local:8091/scoped/upload"
        )


class TestLoadConfig:
    @patch.dict(
        os.environ,
        {
            "UNIQUE_API_KEY": "ukey_test",
            "UNIQUE_APP_ID": "app_test",
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
        },
        clear=False,
    )
    def test_loads_from_env(self) -> None:
        config = load_config()
        assert config.api_key == "ukey_test"
        assert config.app_id == "app_test"
        assert config.user_id == "user_test"
        assert config.company_id == "company_test"
        assert unique_sdk.api_key == "ukey_test"
        assert unique_sdk.app_id == "app_test"

    @patch.dict(
        os.environ,
        {
            "UNIQUE_API_KEY": "ukey_test",
            "UNIQUE_APP_ID": "app_test",
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "UNIQUE_API_BASE": "https://custom.example.com",
        },
        clear=False,
    )
    def test_custom_api_base(self) -> None:
        config = load_config()
        assert config.api_base == "https://custom.example.com"
        assert unique_sdk.api_base == "https://custom.example.com"

    @patch.dict(
        os.environ,
        {
            "UNIQUE_APP_ID": "",
            "UNIQUE_API_KEY": "",
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "UNIQUE_API_BASE": f"'{_TEST_PUBLIC_CHAT_BASE}'",
        },
        clear=True,
    )
    def test_AI_api_base_strips_outer_quotes_from_env(self) -> None:
        """UNIQUE_API_BASE wrapped in pasted quotes resolves to a plain URL."""

        prev = unique_sdk.api_base
        try:
            config = load_config()
            assert config.api_base == _TEST_PUBLIC_CHAT_BASE
            assert unique_sdk.api_base == _TEST_PUBLIC_CHAT_BASE
        finally:
            unique_sdk.api_base = prev

    @patch.dict(
        os.environ,
        {
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
        },
        clear=True,
    )
    def test_api_key_and_app_id_optional(self) -> None:
        config = load_config()
        assert config.api_key == ""
        assert config.app_id == ""
        assert config.user_id == "user_test"
        assert config.company_id == "company_test"

    @patch.dict(
        os.environ,
        {"UNIQUE_API_KEY": "ukey_test"},
        clear=True,
    )
    def test_missing_vars_exits(self) -> None:
        with pytest.raises(SystemExit):
            load_config()

    @patch.dict(os.environ, {}, clear=True)
    def test_all_vars_missing_exits(self) -> None:
        with pytest.raises(SystemExit):
            load_config()


class TestLoadConfigIngestionUpload:
    """``INGESTION_UPLOAD_API_URL_INTERNAL`` env var → SDK module global.

    The CLI is the only place the env var is read; the SDK proper does
    not auto-init from the environment (mirrors the way ``api_key`` is
    surfaced — applications either set ``unique_sdk.api_key`` directly
    or call ``load_config()`` to pull it from the env). These tests pin
    that the wiring writes onto BOTH the returned ``Config`` and the
    package-level ``unique_sdk.ingestion_upload_api_url_internal``
    attribute, with the same empty/whitespace-disable semantics that
    the consumer (``_apply_ingestion_upload_url_override``) uses on the
    read side.
    """

    @patch.dict(
        os.environ,
        {
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "INGESTION_UPLOAD_API_URL_INTERNAL": (
                "http://node-ingestion.test.svc.cluster.local:8091/scoped/upload"
            ),
        },
        clear=True,
    )
    def test_env_var_is_wired_onto_sdk_global(self) -> None:
        config = load_config()
        expected = "http://node-ingestion.test.svc.cluster.local:8091/scoped/upload"
        assert config.ingestion_upload_api_url_internal == expected
        assert unique_sdk.ingestion_upload_api_url_internal == expected

    @patch.dict(
        os.environ,
        {
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
        },
        clear=True,
    )
    def test_unset_env_var_leaves_global_at_none(self) -> None:
        config = load_config()
        assert config.ingestion_upload_api_url_internal is None
        assert unique_sdk.ingestion_upload_api_url_internal is None

    @patch.dict(
        os.environ,
        {
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "INGESTION_UPLOAD_API_URL_INTERNAL": "",
        },
        clear=True,
    )
    def test_empty_env_var_collapses_to_none(self) -> None:
        # Empty string in a Helm overlay is a deliberate "disable the
        # rewrite" knob; the operator should not have to ``unset`` the
        # env var entirely. ``load_config`` collapses it to ``None``
        # so the consumer's ``if not base`` check fires.
        config = load_config()
        assert config.ingestion_upload_api_url_internal is None
        assert unique_sdk.ingestion_upload_api_url_internal is None

    @patch.dict(
        os.environ,
        {
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "INGESTION_UPLOAD_API_URL_INTERNAL": "   ",
        },
        clear=True,
    )
    def test_whitespace_env_var_collapses_to_none(self) -> None:
        # Same contract as the empty-string case: whitespace-only is
        # treated as "disabled" rather than as a literal URL fragment
        # that would later 400 on the upload PUT.
        config = load_config()
        assert config.ingestion_upload_api_url_internal is None
        assert unique_sdk.ingestion_upload_api_url_internal is None

    @patch.dict(
        os.environ,
        {
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "INGESTION_UPLOAD_API_URL_INTERNAL": (
                "  http://node-ingestion/upload  "
            ),
        },
        clear=True,
    )
    def test_surrounding_whitespace_is_trimmed(self) -> None:
        # Operators paste URLs with trailing newlines / spaces all the
        # time; trimming on the wiring layer keeps the URL clean
        # without forcing the override helper to do per-call cleanup.
        config = load_config()
        assert config.ingestion_upload_api_url_internal == (
            "http://node-ingestion/upload"
        )
        assert (
            unique_sdk.ingestion_upload_api_url_internal
            == "http://node-ingestion/upload"
        )
