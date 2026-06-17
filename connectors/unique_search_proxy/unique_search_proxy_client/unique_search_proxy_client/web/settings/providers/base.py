from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import ClassVar, TypeVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from unique_search_proxy_core.errors import EngineNotConfiguredError

NOT_PROVIDED = "NOT_PROVIDED"
"""Sentinel default for required provider secrets when env vars are unset."""


class ProviderCredentials(BaseSettings):
    """Env-backed provider credentials with required-secret checks."""

    _env_prefix: ClassVar[str]

    @lru_cache
    def check_credentials(self) -> None:
        """Raise ``EngineNotConfiguredError`` when required secrets are missing."""
        _check_required_credentials(self, env_prefix=self._env_prefix)


T = TypeVar("T", bound=type[ProviderCredentials])


def provider_credentials(env_prefix: str) -> Callable[[T], T]:
    """Set ``_env_prefix`` on a provider settings class."""

    def decorate(cls: T) -> T:
        cls._env_prefix = env_prefix
        return cls

    return decorate


def _is_secret_configured(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    if not normalized:
        return False
    return normalized != NOT_PROVIDED


def _credential_env_var(field_name: str, env_prefix: str) -> str:
    return f"{env_prefix}{field_name.upper()}"


def _iter_not_provided_credential_fields(model_cls: type[BaseModel]) -> tuple[str, ...]:
    return tuple(
        name
        for name, field_info in model_cls.model_fields.items()
        if field_info.default is NOT_PROVIDED
    )


def _require_provider_secrets(checks: Sequence[tuple[str, str]]) -> None:
    missing_env_vars = [
        env_var for value, env_var in checks if not _is_secret_configured(value)
    ]
    if not missing_env_vars:
        return
    raise EngineNotConfiguredError(missing_env_vars=missing_env_vars)


def _check_required_credentials(credentials: BaseModel, *, env_prefix: str) -> None:
    checks: list[tuple[str, str]] = []
    for attr in _iter_not_provided_credential_fields(type(credentials)):
        checks.append(
            (getattr(credentials, attr), _credential_env_var(attr, env_prefix))
        )
    _require_provider_secrets(checks)
