from __future__ import annotations

from collections.abc import Callable

import pytest

from unique_search_proxy_client.web.settings.secret_str import (
    NOT_PROVIDED,
    LogSecretStr,
    _mask_secret_for_display,
)


@pytest.fixture
def patch_startup_log_suffix_len(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[int], None]:
    """Set ``startup_log_settings.secret_suffix_len`` for the duration of a test."""

    def _patch(suffix_len: int) -> None:
        import unique_search_proxy_client.web.settings.secret_str as secret_str_module
        from unique_search_proxy_client.web.settings.secret_str import (
            StartupLogSettings,
        )

        monkeypatch.setattr(
            secret_str_module,
            "startup_log_settings",
            StartupLogSettings(secret_suffix_len=suffix_len),
        )

    return _patch


class TestMaskSecretForDisplay:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("", ""),
            (NOT_PROVIDED, NOT_PROVIDED),
        ],
        ids=["empty", "not_provided"],
    )
    def test_mask_secret_for_display__special_values(
        self,
        patch_startup_log_suffix_len: Callable[[int], None],
        value: str,
        expected: str,
    ) -> None:
        """
        Purpose: Verify empty and sentinel values bypass masking rules.

        Why this matters: Startup logs must show NOT_PROVIDED literally and never crash on empty secrets.

        Setup summary: suffix_len=3; assert _mask_secret_for_display returns value unchanged.
        """
        patch_startup_log_suffix_len(3)
        assert _mask_secret_for_display(value) == expected

    @pytest.mark.ai
    def test_mask_secret_for_display__suffix_len_zero_hides_all(
        self,
        patch_startup_log_suffix_len: Callable[[int], None],
    ) -> None:
        """
        Purpose: Verify suffix_len=0 always emits a fixed-width mask.

        Why this matters: Operators who disable suffix logging must never see secret fragments.

        Setup summary: suffix_len=0; assert short and long secrets both render as ten asterisks.
        """
        patch_startup_log_suffix_len(0)
        assert _mask_secret_for_display("short") == "**********"
        assert _mask_secret_for_display("a" * 100) == "**********"

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("suffix_len", "secret", "expected"),
        [
            (3, "ab", "**********"),
            (3, "test-key", "**********"),
            (3, "Bearer secret-token", "**********"),
            (3, "a" * 30, "**********"),
            (3, "a" * 28 + "xyz", "**********xyz"),
            (5, "abcdefghij", "**********"),
            (5, "a" * 50, "**********"),
            (5, "a" * 45 + "hello", "**********"),
            (5, "a" * 46 + "hello", "**********hello"),
            (8, "a" * 80, "**********"),
            (8, "a" * 73 + "token123", "**********token123"),
        ],
        ids=[
            "suffix3-short-2-chars",
            "suffix3-short-8-chars",
            "suffix3-short-18-chars",
            "suffix3-boundary-30-chars-full-mask",
            "suffix3-boundary-31-chars-shows-suffix",
            "suffix5-short-10-chars",
            "suffix5-boundary-50-chars-full-mask",
            "suffix5-boundary-50-chars-at-threshold",
            "suffix5-boundary-51-chars-shows-suffix",
            "suffix8-boundary-80-chars-full-mask",
            "suffix8-boundary-81-chars-shows-suffix",
        ],
    )
    def test_mask_secret_for_display__length_thresholds(
        self,
        patch_startup_log_suffix_len: Callable[[int], None],
        suffix_len: int,
        secret: str,
        expected: str,
    ) -> None:
        """
        Purpose: Verify masking follows the 10% length threshold for varied suffix_len values.

        Why this matters: Short secrets must be fully redacted; only long secrets may reveal a suffix.

        Setup summary: Patch suffix_len; assert _mask_secret_for_display output per case.
        """
        patch_startup_log_suffix_len(suffix_len)
        assert _mask_secret_for_display(secret) == expected

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("suffix_len", "secret", "expected"),
        [
            (3, "a" * 28 + "xyz", "**********xyz"),
            (5, "a" * 46 + "hello", "**********hello"),
            (8, "a" * 73 + "token123", "**********token123"),
        ],
        ids=["suffix3", "suffix5", "suffix8"],
    )
    def test_log_secret_str_matches_mask_helper(
        self,
        patch_startup_log_suffix_len: Callable[[int], None],
        suffix_len: int,
        secret: str,
        expected: str,
    ) -> None:
        """
        Purpose: Verify LogSecretStr str()/repr() delegate to the same masking helper.

        Why this matters: Startup logs and settings formatting must stay consistent with LogSecretStr.

        Setup summary: Patch suffix_len; assert str/repr on LogSecretStr match expected mask.
        """
        patch_startup_log_suffix_len(suffix_len)
        assert str(LogSecretStr(secret)) == expected
        assert repr(LogSecretStr(secret)) == f"LogSecretStr('{expected}')"
