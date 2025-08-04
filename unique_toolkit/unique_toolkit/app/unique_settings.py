from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class UniqueApp(BaseSettings):
    id: SecretStr
    key: SecretStr
    base_url: str
    endpoint: str
    endpoint_secret: SecretStr

    model_config = SettingsConfigDict(
        env_prefix="unique_app_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class UniqueAuth(BaseSettings):
    company_id: SecretStr
    user_id: SecretStr

    model_config = SettingsConfigDict(
        env_prefix="unique_auth_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class UniqueSettings:
    def __init__(self, auth: UniqueAuth, app: UniqueApp):
        self.app = app
        self.auth = auth

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
        auth = UniqueAuth(_env_file=env_file_str, _env_file_encoding="utf-8")
        app = UniqueApp(_env_file=env_file_str, _env_file_encoding="utf-8")

        return cls(auth=auth, app=app)
