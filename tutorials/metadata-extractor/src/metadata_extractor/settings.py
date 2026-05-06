from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root .env: we are in src/metadata_extractor/, so go up two levels
env_file_path = (Path(__file__).parent / ".." / ".." / ".env").resolve()


class MetadataExtractorSettings(BaseSettings):
    endpoint_secret: str = ""
    content_url: str = ""
    token_url: str = ""
    user_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    project_id: str = ""
    base_url: str = ""
    company_id: str = ""
    app_id: str = ""
    api_key: str = ""
    assistant_id: str = ""
    subscriptions: list[str] = []
    env: str = ""

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        extra="ignore",
    )


def get_settings() -> MetadataExtractorSettings:
    return MetadataExtractorSettings()
