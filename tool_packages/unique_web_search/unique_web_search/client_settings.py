import logging

from pydantic import BaseModel

from unique_web_search.settings import env_settings

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class GoogleSearchSettings(BaseModel):
    api_key: str | None = None
    search_engine_id: str | None = None
    api_endpoint: str | None = None

    @property
    def is_configured(self) -> bool:
        return (
            self.api_key and self.search_engine_id and self.api_endpoint
        ) is not None

    @classmethod
    def from_env_settings(cls):
        missing_settings = []

        if env_settings.google_search_api_key is None:
            missing_settings.append("API Key")
        if env_settings.google_search_engine_id is None:
            missing_settings.append("Engine ID")
        if env_settings.google_search_api_endpoint is None:
            missing_settings.append("API Endpoint")

        if missing_settings:
            logger.warning(
                f"Google Search API missing required settings: {', '.join(missing_settings)}"
            )
        else:
            logger.info("Google Search API is properly configured")

        return cls(
            api_key=env_settings.google_search_api_key,
            search_engine_id=env_settings.google_search_engine_id,
            api_endpoint=env_settings.google_search_api_endpoint,
        )


_google_search_settings: GoogleSearchSettings | None = None


def get_google_search_settings() -> GoogleSearchSettings:
    global _google_search_settings
    if _google_search_settings is None:
        _google_search_settings = GoogleSearchSettings.from_env_settings()
    return _google_search_settings


class FirecrawlSearchSettings(BaseModel):
    api_key: str | None = None

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None

    @classmethod
    def from_env_settings(cls):
        missing_settings = []

        if env_settings.firecrawl_api_key is None:
            missing_settings.append("API Key")

        if missing_settings:
            logger.warning(
                f"Firecrawl Search API missing required settings: {', '.join(missing_settings)}"
            )
        else:
            logger.info("Firecrawl Search API is properly configured")

        return cls(
            api_key=env_settings.firecrawl_api_key,
        )


_firecrawl_search_settings: FirecrawlSearchSettings | None = None


def get_firecrawl_search_settings() -> FirecrawlSearchSettings:
    global _firecrawl_search_settings
    if _firecrawl_search_settings is None:
        _firecrawl_search_settings = FirecrawlSearchSettings.from_env_settings()
    return _firecrawl_search_settings


class JinaSearchSettings(BaseModel):
    api_key: str | None = None
    search_api_endpoint: str = env_settings.jina_search_api_endpoint
    reader_api_endpoint: str = env_settings.jina_reader_api_endpoint

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None

    @classmethod
    def from_env_settings(cls):
        missing_settings = []

        if env_settings.jina_api_key is None:
            missing_settings.append("API Key")

        if missing_settings:
            logger.warning(
                f"Jina Search API missing required settings: {', '.join(missing_settings)}"
            )
        else:
            logger.info("Jina Search API is properly configured")

        return cls(
            api_key=env_settings.jina_api_key,
        )


_jina_search_settings: JinaSearchSettings | None = None


def get_jina_search_settings() -> JinaSearchSettings:
    global _jina_search_settings
    if _jina_search_settings is None:
        _jina_search_settings = JinaSearchSettings.from_env_settings()
    return _jina_search_settings


class TavilySearchSettings(BaseModel):
    api_key: str | None = None

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None

    @classmethod
    def from_env_settings(cls):
        missing_settings = []

        if env_settings.tavily_api_key is None:
            missing_settings.append("API Key")

        if missing_settings:
            logger.warning(
                f"Tavily Search API missing required settings: {', '.join(missing_settings)}"
            )
        else:
            logger.info("Tavily Search API is properly configured")

        return cls(api_key=env_settings.tavily_api_key)


_tavily_search_settings: TavilySearchSettings | None = None


def get_tavily_search_settings() -> TavilySearchSettings:
    global _tavily_search_settings
    if _tavily_search_settings is None:
        _tavily_search_settings = TavilySearchSettings.from_env_settings()
    return _tavily_search_settings
