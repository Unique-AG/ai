from typing import override

from pydantic import BaseModel, Field
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    BraveSearchRequest,
)

from unique_web_search.client_settings import get_brave_search_settings
from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


class BraveSearchConfig(BraveConfig):
    requires_scraping: bool = Field(
        default=False,
        title="Requires scraping",
        description=(
            "Crawl every search result and pass the full page content to the "
            "model instead of only the Brave snippets."
        ),
    )

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """Use the proxy's wire contract, excluding tool-only configuration fields."""
        return BraveSearchRequest


@register_search_engine(
    name="brave",
    key=SearchEngineType.BRAVE,
    config_cls=BraveSearchConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Brave",
)
class BraveSearch(SearchEngine[BraveSearchConfig]):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.is_configured = (
            search_proxy_client_enabled or get_brave_search_settings().is_configured
        )

    @property
    def requires_scraping(self) -> bool:
        return getattr(self.config, "requires_scraping", False)

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        raise NotImplementedError("Brave search is not supported in the legacy mode")
