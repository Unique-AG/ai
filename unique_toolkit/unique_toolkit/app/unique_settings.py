from logging import getLogger
from pathlib import Path
from typing import Self, TypeVar
from urllib.parse import urlparse, urlunparse

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = getLogger(__name__)

T = TypeVar("T", bound=BaseSettings)


def warn_about_defaults(instance: T) -> T:
    """Log warnings for fields that are using default values."""
    for field_name, model_field in instance.__class__.model_fields.items():
        field_value = getattr(instance, field_name)
        default_value = model_field.default

        # Handle SecretStr comparison by comparing the secret values
        if isinstance(field_value, SecretStr) and isinstance(default_value, SecretStr):
            if field_value.get_secret_value() == default_value.get_secret_value():
                logger.warning(
                    f"Using default value for '{field_name}': {default_value.get_secret_value()}"
                )
        elif field_value == default_value:
            logger.warning(f"Using default value for '{field_name}': {default_value}")
    return instance


class UniqueApp(BaseSettings):
    id: SecretStr = Field(
        default=SecretStr("dummy_id"),
        validation_alias=AliasChoices(
            "unique_app_id", "app_id", "UNIQUE_APP_ID", "APP_ID"
        ),
    )
    key: SecretStr = Field(
        default=SecretStr("dummy_key"),
        validation_alias=AliasChoices(
            "unique_app_key", "key", "UNIQUE_APP_KEY", "KEY", "API_KEY", "api_key"
        ),
    )
    base_url: str = Field(
        default="http://localhost:8092/",
        deprecated="Use UniqueApi.base_url instead",
    )
    endpoint: str = Field(default="dummy")
    endpoint_secret: SecretStr = Field(default=SecretStr("dummy_secret"))

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)

    model_config = SettingsConfigDict(
        env_prefix="unique_app_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class UniqueApi(BaseSettings):
    base_url: str = Field(
        default="http://localhost:8092/",
        description="The base URL of the Unique API. Ask your admin to provide you with the correct URL.",
        validation_alias=AliasChoices(
            "unique_api_base_url", "base_url", "UNIQUE_API_BASE_URL", "BASE_URL"
        ),
    )
    version: str = Field(
        default="2023-12-06",
        validation_alias=AliasChoices(
            "unique_api_version", "version", "UNIQUE_API_VERSION", "VERSION"
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="unique_api_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)

    def sse_url(self, subscriptions: list[str]) -> str:
        parsed = urlparse(self.base_url)
        return urlunparse(
            parsed._replace(
                path="/public/event-socket/events/stream",
                query=f"subscriptions={','.join(subscriptions)}",
                fragment=None,
            )
        )

    def sdk_url(self) -> str:
        parsed = urlparse(self.base_url)

        path = "/public/chat"
        if parsed.hostname and "qa.unique" in parsed.hostname:
            path = "/public/chat-gen2"
        return urlunparse(parsed._replace(path=path, query=None, fragment=None))

    def openai_proxy_url(self) -> str:
        parsed = urlparse(self.base_url)
        path = "/public/chat/openai-proxy/"
        if parsed.hostname and "qa.unique" in parsed.hostname:
            path = "/public/chat-gen2/openai-proxy/"

        return urlunparse(parsed._replace(path=path, query=None, fragment=None))


class UniqueAuth(BaseSettings):
    company_id: SecretStr = Field(
        default=SecretStr("dummy_company_id"),
        validation_alias=AliasChoices(
            "unique_auth_company_id",
            "company_id",
            "UNIQUE_AUTH_COMPANY_ID",
            "COMPANY_ID",
        ),
    )
    user_id: SecretStr = Field(
        default=SecretStr("dummy_user_id"),
        validation_alias=AliasChoices(
            "unique_auth_user_id", "user_id", "UNIQUE_AUTH_USER_ID", "USER_ID"
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="unique_auth_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)


class UniqueSettings:
    def __init__(self, auth: UniqueAuth, app: UniqueApp, api: UniqueApi):
        self.app = app
        self.auth = auth
        self.api = api

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "UniqueSettings":
        """Initialize settings from environment variables and/or env file.

        Args:
            env_file: Optional path to environment file. If provided, will load variables from this file.

        Returns:
            UniqueSettings instance with values loaded from environment/env file.

        Raises:
            FileNotFoundError: If env_file is provided but does not exist.
            ValidationError: If required environment variables are missing.
        """
        if env_file and not env_file.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file}")

        # Initialize settings with environment file if provided
        env_file_str = str(env_file) if env_file else None
        auth = UniqueAuth(_env_file=env_file_str)  # type: ignore[call-arg]
        app = UniqueApp(_env_file=env_file_str)  # type: ignore[call-arg]
        api = UniqueApi(_env_file=env_file_str)  # type: ignore[call-arg]
        return cls(auth=auth, app=app, api=api)
