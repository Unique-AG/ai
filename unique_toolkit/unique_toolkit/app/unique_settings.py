# %%

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

config_dict = SettingsConfigDict(
    env_file=Path(__file__).parent.parent / ".env",
    env_file_encoding="utf-8",
    extra="ignore",
)


class UniqueApp(BaseSettings):
    id: str
    key: str
    base_url: str
    endpoint: str
    endpoint_secret: str

    model_config = SettingsConfigDict(env_prefix="unique_app_", **config_dict)


class UniqueAuth(BaseSettings):
    company_id: str
    user_id: str

    model_config = SettingsConfigDict(env_prefix="unique_auth_", **config_dict)


class UniqueSettings:
    app: UniqueApp = UniqueApp()
    auth: UniqueAuth = UniqueAuth()


# %%
