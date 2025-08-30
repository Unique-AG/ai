import logging
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# TODO: Clean this up from monorepo. Its mixing everything

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class Base(BaseSettings):
    save_to_local_file: bool = Field(
        default=False,
        description="Save conversation to local file. DO NOT USE THIS IN PRODUCTION!",
    )
    debug_file_folder: str | None = Field(
        default=None,
        description="Folder to save conversation to. DO NOT USE THIS IN PRODUCTION!",
    )

    env: str | None = None
    log_level: str | None = None
    tiktoken_cache_dir: str = "./tiktoken_cache/"

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

    # Custom chat error message
    custom_chat_error_message: str | None = None

    # Quartr Creds
    quartr_api_creds: str | None = None
    quartr_api_activated_companies: list[str] = []

    # Six API Creds
    six_api_creds: str | None = None
    six_api_activated_companies: list[str] = []

    # SQL Database
    database_mode: Literal["sqlite", "postgresql"] = "sqlite"
    database_url: str | None = None  # Must be supplied for postgresql

    # Variables only used during testing
    test_company_id: str = ""
    test_user_id: str = ""
    test_chat_id: str = ""
    test_assistant_id: str = ""
    test_user_message_id: str = ""
    test_scope_id: str = ""
    test_run_integration_test: bool = False

    # Evaluation framework
    enable_opik: bool = False


class Settings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env", extra="ignore"
    )


class TestSettings(Base):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / "tests/test.env", extra="ignore"
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
