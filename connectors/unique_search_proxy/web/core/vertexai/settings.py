from pydantic_settings import BaseSettings, SettingsConfigDict
from settings import get_env_path


class VertexAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_path(), env_file_encoding="utf-8", env_prefix="vertexai_"
    )
    service_account_credentials: str | None = None
