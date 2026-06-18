import logging

import pytest

from unique_search_proxy_client.web.settings.providers.base import NOT_PROVIDED
from unique_search_proxy_client.web.settings.providers.google import (
    _get_google_search_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr
from unique_search_proxy_client.web.settings.startup_report import (
    _field_status,
    build_startup_settings_report,
    log_startup_settings_report,
)


class TestStartupSettingsReport:
    @pytest.mark.ai
    def test_log_secret_str_masks_suffix_in_str(self) -> None:
        assert str(LogSecretStr("abcdefghijklmnop")) == "**********nop"
        assert str(LogSecretStr("test-key")) == "**********key"
        assert str(LogSecretStr("ab")) == "**"
        assert str(LogSecretStr(NOT_PROVIDED)) == NOT_PROVIDED
        assert repr(LogSecretStr("abcdefghijklmnop")) == (
            "LogSecretStr('**********nop')"
        )

    @pytest.mark.ai
    def test_startup_log_secret_suffix_len_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from unique_search_proxy_client.web.settings.startup_log import (
            _get_startup_log_settings,
        )

        monkeypatch.setenv("STARTUP_LOG_SECRET_SUFFIX_LEN", "5")
        assert _get_startup_log_settings().secret_suffix_len == 5

    @pytest.mark.ai
    def test_field_status_marks_missing_provider_secrets(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify required provider secrets are reported as missing when unset.

        Why this matters: Startup logs must flag unavailable engines before traffic hits them.

        Setup summary: Unset Google credentials; assert api_key is missing and endpoint is default.
        """
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", NOT_PROVIDED)
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", NOT_PROVIDED)
        monkeypatch.delenv("GOOGLE_SEARCH_API_ENDPOINT", raising=False)
        credentials = _get_google_search_credentials()

        assert _field_status(credentials, "api_key", "GOOGLE_SEARCH_") == "missing"
        assert _field_status(credentials, "engine_id", "GOOGLE_SEARCH_") == "missing"
        assert _field_status(credentials, "api_endpoint", "GOOGLE_SEARCH_") == "default"

    @pytest.mark.ai
    def test_build_startup_settings_report_groups_by_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify the report groups env vars under status labels for readability.

        Why this matters: Operators need to scan missing/unset vars without reading long lines.

        Setup summary: Unset Google secrets; assert report shows incomplete group and missing vars.
        """
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", NOT_PROVIDED)
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", NOT_PROVIDED)

        report = build_startup_settings_report()

        assert "[Google Search] incomplete (2 missing)" in report
        assert "GOOGLE_SEARCH_API_KEY=NOT_PROVIDED" in report
        assert "GOOGLE_SEARCH_ENGINE_ID=NOT_PROVIDED" in report
        assert "[Runtime] LOG_LEVEL=" in report

    @pytest.mark.ai
    def test_log_startup_settings_report_emits_single_message(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Purpose: Verify startup logging emits one multi-line record instead of many lines.

        Why this matters: A single log entry avoids repeated logger prefixes in pod output.

        Setup summary: Capture INFO logs from report helper; assert one settings block message.
        """
        caplog.set_level(logging.INFO)
        test_logger = logging.getLogger("test.startup_settings_report")

        log_startup_settings_report(logger=test_logger)

        settings_records = [
            record
            for record in caplog.records
            if "Search Proxy settings at startup" in record.message
        ]
        assert len(settings_records) == 1
        message = settings_records[0].message
        assert "[Google Search]" in message
        assert "[URL Safety]" in message
        assert "[Runtime] LOG_LEVEL=" in message
