from logging import getLogger
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = getLogger(__name__)


class BaseSettingsWithWarnings(BaseSettings):
    def __init__(self, **values):
        super().__init__(**values)
        for field_name, model_field in BaseSettingsWithWarnings.model_fields.items():
            if (
                field_name not in values
                and getattr(self, field_name) == model_field.default
            ):
                logger.warning(
                    f"Using default value for '{field_name}': {model_field.default}"
                )


class UniqueApp(BaseSettingsWithWarnings):
    id: SecretStr = Field(default=SecretStr("dummy_id"))
    key: SecretStr = Field(default=SecretStr("dummy_key"))
    base_url: str = Field(
        default="http://localhost:8092/public",
        deprecated="Use UniqueApi.base_url instead",
    )
    endpoint: str = Field(default="dummy")
    endpoint_secret: SecretStr = Field(default=SecretStr("dummy_secret"))

    model_config = SettingsConfigDict(
        env_prefix="unique_app_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class UniqueApi(BaseSettingsWithWarnings):
    base_url: str = Field(default="http://localhost:8092/public")
    version: str = Field(default="2023-12-06")

    model_config = SettingsConfigDict(
        env_prefix="unique_api_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class UniqueAuth(BaseSettingsWithWarnings):
    company_id: SecretStr = Field(default=SecretStr("dummy_company_id"))
    user_id: SecretStr = Field(default=SecretStr("dummy_user_id"))

    model_config = SettingsConfigDict(
        env_prefix="unique_auth_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


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
        auth = UniqueAuth(_env_file=env_file_str)
        app = UniqueApp(_env_file=env_file_str)
        api = UniqueApi(_env_file=env_file_str)
        return cls(auth=auth, app=app, api=api)
