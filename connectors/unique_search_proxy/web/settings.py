import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

CWD = Path(os.getcwd())


class Base(BaseSettings):
    # Google Search settings
    google_search_api_key: str | None = None
    google_search_api_endpoint: str | None = None
    google_search_engine_id: str | None = None

    # VertexAI API settings
    vertexai_service_account_credentials: str | None = None


class Settings(Base):
    model_config = SettingsConfigDict(env_file=CWD / ".env", env_file_encoding="utf-8")


env_settings = Settings()
