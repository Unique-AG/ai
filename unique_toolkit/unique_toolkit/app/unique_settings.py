import os
from logging import getLogger
from pathlib import Path
from typing import Self, TypeVar
from urllib.parse import ParseResult, urlparse, urlunparse

import unique_sdk
from platformdirs import user_config_dir
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

    def base_path(self) -> tuple[ParseResult, str]:
        parsed = urlparse(self.base_url)
        base_path = "/public/chat/"

        if parsed.hostname and (
            "gateway.qa.unique" in parsed.hostname
            or "gateway.unique" in parsed.hostname
        ):
            base_path = "/public/chat-gen2/"

        if parsed.hostname and "localhost" in parsed.hostname:
            base_path = "/public/"

        return parsed, base_path

    def sdk_url(self) -> str:
        parsed, base_path = self.base_path()
        return urlunparse(parsed._replace(path=base_path, query=None, fragment=None))

    def openai_proxy_url(self) -> str:
        parsed, base_path = self.base_path()
        path = base_path + "openai-proxy/"
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


class EnvFileNotFoundError(FileNotFoundError):
    """Raised when no environment file can be found in any of the expected locations."""


class UniqueSettings:
    def __init__(self, auth: UniqueAuth, app: UniqueApp, api: UniqueApi):
        self.app = app
        self.auth = auth
        self.api = api

    @classmethod
    def _find_env_file(cls, filename: str = "unique.env") -> Path:
        """Find environment file using cross-platform fallback locations.

        Search order:
        1. UNIQUE_ENV_FILE environment variable
        2. Current working directory
        3. User config directory (cross-platform via platformdirs)

        Args:
            filename: Name of the environment file (default: 'unique.env')

        Returns:
            Path to the environment file.

        Raises:
            EnvFileNotFoundError: If no environment file is found in any location.
        """
        locations = [
            # 1. Explicit environment variable
            Path(env_path) if (env_path := os.environ.get("UNIQUE_ENV_FILE")) else None,
            # 2. Current working directory
            Path.cwd() / filename,
            # 3. User config directory (cross-platform)
            Path(user_config_dir("unique", "unique-toolkit")) / filename,
        ]

        for location in locations:
            if location and location.exists() and location.is_file():
                return location

        # If no file found, provide helpful error message
        searched_locations = [str(loc) for loc in locations if loc is not None]
        raise EnvFileNotFoundError(
            f"Environment file '{filename}' not found. Searched locations:\n"
            + "\n".join(f"  - {loc}" for loc in searched_locations)
            + "\n\nTo fix this:\n"
            + f"  1. Create {filename} in one of the above locations, or\n"
            + f"  2. Set UNIQUE_ENV_FILE environment variable to point to your {filename} file"
        )

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

    @classmethod
    def from_env_auto(cls, filename: str = "unique.env") -> "UniqueSettings":
        """Initialize settings by automatically finding environment file.

        This method will automatically search for an environment file in standard locations
        and fall back to environment variables only if no file is found.

        Args:
            filename: Name of the environment file to search for (default: '.env')

        Returns:
            UniqueSettings instance with values loaded from found env file or environment variables.
        """
        try:
            env_file = cls._find_env_file(filename)
            return cls.from_env(env_file=env_file)
        except EnvFileNotFoundError:
            logger.warning(
                f"Environment file '{filename}' not found. Falling back to environment variables only."
            )
            # Fall back to environment variables only
            return cls.from_env()

    def init_sdk(self) -> None:
        """Initialize the unique_sdk global configuration with these settings.

        This method configures the global unique_sdk module with the API key,
        app ID, and base URL from these settings.
        """
        unique_sdk.api_key = self.app.key.get_secret_value()
        unique_sdk.app_id = self.app.id.get_secret_value()
        unique_sdk.api_base = self.api.sdk_url()

    @classmethod
    def from_env_auto_with_sdk_init(
        cls, filename: str = "unique.env"
    ) -> "UniqueSettings":
        """Initialize settings and SDK in one convenient call.

        This method combines from_env_auto() and init_sdk() for the most common use case.

        Args:
            filename: Name of the environment file to search for (default: '.env')

        Returns:
            UniqueSettings instance with SDK already initialized.
        """
        settings = cls.from_env_auto(filename)
        settings.init_sdk()
        return settings
