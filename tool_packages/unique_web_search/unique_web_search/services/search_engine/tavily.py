import logging
from typing import Literal, Sequence, Union

from pydantic import BaseModel, Field, ValidationError
from tavily import AsyncTavilyClient
from unique_toolkit.tools.config import get_configuration_dict

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.settings import env_settings

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class ImageResult(BaseModel):
    url: str
    description: str


class TavilyResult(BaseModel):
    title: str
    url: str
    content: str
    score: float
    raw_content: str | None = None
    published_date: str | None = None
    favicon: str | None = None


class TavilySearchResponse(BaseModel):
    results: list[TavilyResult]
    query: str
    response_time: float
    answer: str | None = None
    images: list[str | ImageResult] | None = None
    request_id: str


class TavilySearchSettings(BaseModel):
    api_key: str | None = Field(..., description="The API key for the Tavily API")

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


class TavilySearchParams(BaseModel):
    query: str
    max_results: int = 5
    search_depth: Literal["basic", "advanced"] | None = None
    topic: Literal["general", "news", "finance"] | None = None
    time_range: Literal["day", "week", "month", "year"] | None = None
    start_date: str | None = None
    end_date: str | None = None
    days: int | None = None

    include_domains: Sequence[str] | None = None
    exclude_domains: Sequence[str] | None = None
    include_images: bool = False
    timeout: int = 60
    country: str | None = None
    auto_parameters: bool | None = None

    include_favicon: bool | None = False
    include_answer: Union[bool, Literal["basic", "advanced"]] = False
    include_raw_content: Union[bool, Literal["markdown", "text"]] = "markdown"


class TavilyCustomSearchConfig(BaseModel):
    model_config = get_configuration_dict()
    search_depth: Literal["basic", "advanced"] = "advanced"
    topic: Literal["general", "news", "finance"] | None = None


class TavilyConfig(BaseSearchEngineConfig[SearchEngineType.TAVILY]):
    search_engine_name: Literal[SearchEngineType.TAVILY] = SearchEngineType.TAVILY
    custom_search_config: TavilyCustomSearchConfig = TavilyCustomSearchConfig()


_tavily_search_settings: TavilySearchSettings | None = None


def get_tavily_search_settings() -> TavilySearchSettings:
    global _tavily_search_settings
    if _tavily_search_settings is None:
        _tavily_search_settings = TavilySearchSettings.from_env_settings()
    return _tavily_search_settings


class TavilySearch(SearchEngine[TavilyConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.is_configured = get_tavily_search_settings().is_configured

    @property
    def requires_scraping(self) -> bool:
        return False

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        tavily_search_settings = get_tavily_search_settings()
        assert tavily_search_settings.is_configured

        client = AsyncTavilyClient(api_key=tavily_search_settings.api_key)
        search_params = TavilySearchParams(
            query=query,
            max_results=self.config.fetch_size,
            **self.config.custom_search_config.model_dump(
                exclude_none=True, by_alias=False
            ),
        )

        response = await client.search(**search_params.model_dump(exclude_none=True))

        try:
            validated_response = TavilySearchResponse.model_validate(response)
        except ValidationError as e:
            logger.error(f"Invalid response from Tavily: {e}")
            return []

        return [
            WebSearchResult(
                url=result.url,
                title=result.title,
                snippet=result.content,
                content=result.raw_content or result.content,
            )
            for result in validated_response.results
        ]
