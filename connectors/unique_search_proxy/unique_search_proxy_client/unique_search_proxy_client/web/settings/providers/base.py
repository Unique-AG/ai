from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import ClassVar, TypeVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.settings.secret_str import (
    field_has_not_provided_default,
    is_secret_configured,
)


class ProviderCredentials(BaseSettings):
    """Env-backed provider credentials with required-secret checks."""

    _env_prefix: ClassVar[str]

    @lru_cache
    def check_credentials(self) -> None:
        """Raise ``EngineNotConfiguredError`` when required secrets are missing."""
        _check_required_credentials(self, env_prefix=self._env_prefix)


T = TypeVar("T", bound=type[ProviderCredentials])


def provider_credentials(env_prefix: str) -> Callable[[T], T]:
    """Mark a class as an env-backed credential provider.

    Owns ``_env_prefix`` only — used by ``check_credentials`` to build env var
    names for missing-secret errors. Helm-registry metadata (title, ``helm_key``,
    egress, …) is attached separately and independently via ``@helm_settings``.
    """

    def decorate(cls: T) -> T:
        cls._env_prefix = env_prefix
        return cls

    return decorate


def _credential_env_var(field_name: str, env_prefix: str) -> str:
    return f"{env_prefix}{field_name.upper()}"


def _iter_not_provided_credential_fields(model_cls: type[BaseModel]) -> tuple[str, ...]:
    return tuple(
        name
        for name, field_info in model_cls.model_fields.items()
        if field_has_not_provided_default(field_info)
    )


def _require_provider_secrets(checks: Sequence[tuple[str, str]]) -> None:
    missing_env_vars = [
        env_var for value, env_var in checks if not is_secret_configured(value)
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
