from __future__ import annotations

from collections.abc import Mapping

from pydantic import SecretStr

_NOT_PROVIDED = "NOT_PROVIDED"


def _secret_log_suffix_len() -> int:
    from unique_search_proxy_client.web.settings.startup_log import (
        startup_log_settings,
    )

    return startup_log_settings.secret_suffix_len


def _mask_secret_for_display(value: str) -> str:
    if not value:
        return ""
    if value == _NOT_PROVIDED:
        return _NOT_PROVIDED
    suffix_len = _secret_log_suffix_len()
    if suffix_len <= 0:
        return "*" * 10
    # 20% of the value length is the max suffix length
    if len(value) * 0.10 <= suffix_len:
        return "*" * 10
    return f"**********{value[-suffix_len:]}"


class LogSecretStr(SecretStr):
    """SecretStr that masks values in str()/repr() with a configurable suffix."""

    def _display(self) -> str:
        return _mask_secret_for_display(self._secret_value)


def read_secret_headers(headers: Mapping[str, LogSecretStr]) -> dict[str, str]:
    """Unwrap proxy header secrets for httpx."""
    return {name: value.get_secret_value() for name, value in headers.items()}
