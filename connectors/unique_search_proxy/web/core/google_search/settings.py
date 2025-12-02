from settings import get_env_path
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleSearchSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_path(), env_file_encoding="utf-8", env_prefix="google_search_"
    )
    api_key: str | None = None
    api_endpoint: str | None = None
    engine_id: str | None = None
