import logging
import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# TODO: Clean this up from monorepo. Its mixing everything

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class Base(BaseSettings):
    env: str | None = None
    log_level: str | None = None
    tiktoken_cache_dir: str = "./tiktoken_cache/"

    # Active search engines
    active_search_engines: list[str] = ["google"]

    # Bing settings
    bing_search_v7_subscription_key: str | None = None
    bing_api_endpoint: str | None = None

    # Google Search settings
    google_search_api_key: str | None = None
    google_search_api_endpoint: str | None = None
    google_search_engine_id: str | None = None

    # Jina API settings
    jina_api_key: str | None = None
    jina_search_api_endpoint: str = "https://s.jina.ai/"
    jina_reader_api_endpoint: str = "https://r.jina.ai/"

    # Firecrawl API settings
    firecrawl_api_key: str | None = None

    # Tavily API settings
    tavily_api_key: str | None = None

    # Brave Search API settings
    brave_search_api_key: str | None = None
    brave_search_api_endpoint: str | None = None


class Settings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / ".env", extra="ignore"
    )


class TestSettings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(os.getcwd()) / "tests/test.env", extra="ignore"
    )


def get_settings() -> Base:
    """
    Dynamically load settings, switching to test environment if running under pytest.

    :return: Settings instance.
    """
    if "pytest" in sys.modules:
        # Dynamically adjust to use `test.env` if running under pytest
        return TestSettings()
    return Settings()


env_settings: Base = get_settings()
