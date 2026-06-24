"""Foundational secret-value handling: masking, status checks, and the secret type.

This is the single home for the secret primitives shared across settings:
the ``NOT_PROVIDED`` sentinel, the ``LogSecretStr`` masked type, the masking
configuration (``StartupLogSettings``), and the "is this secret configured"
status helpers consumed by provider credential checks, the startup report, and
the Helm field introspection.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.settings.base import get_settings

NOT_PROVIDED = "NOT_PROVIDED"
"""Sentinel default for required secrets when env vars are unset."""

STARTUP_LOG_ENV_PREFIX = "STARTUP_LOG_"


class StartupLogSettings(BaseSettings):
    """Startup log formatting options."""

    secret_suffix_len: int = Field(
        default=0,
        ge=0,
        le=32,
        description=(
            "Number of trailing characters to show when logging secret values "
            "at startup (0 hides the secret entirely)."
        ),
    )


def _get_startup_log_settings() -> StartupLogSettings:
    return get_settings(StartupLogSettings, env_prefix=STARTUP_LOG_ENV_PREFIX)


startup_log_settings = _get_startup_log_settings()


def _mask_secret_for_display(value: str) -> str:
    if not value:
        return ""
    if value == NOT_PROVIDED:
        return NOT_PROVIDED
    suffix_len = startup_log_settings.secret_suffix_len
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


def read_secret(value: str | SecretStr | None) -> str:
    """Unwrap a secret/plain value to its string (empty string for ``None``)."""
    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def read_secret_headers(headers: Mapping[str, LogSecretStr]) -> dict[str, str]:
    """Unwrap proxy header secrets for httpx."""
    return {name: value.get_secret_value() for name, value in headers.items()}


def is_secret_configured(value: str | SecretStr | None) -> bool:
    """True when a secret holds a real, non-sentinel value."""
    normalized = read_secret(value).strip()
    if not normalized:
        return False
    return normalized != NOT_PROVIDED


def field_has_not_provided_default(field_info: object) -> bool:
    """True when a model field defaults to the ``NOT_PROVIDED`` sentinel."""
    default = getattr(field_info, "default", None)
    if default is NOT_PROVIDED:
        return True
    if isinstance(default, SecretStr):
        return default.get_secret_value() == NOT_PROVIDED
    return False
