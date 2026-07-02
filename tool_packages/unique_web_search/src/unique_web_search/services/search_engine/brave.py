from typing import override

from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig

from unique_web_search.client_settings import get_brave_search_settings
from unique_web_search.services.proxy.bridge import (
    open_search_proxy_client,
    search_proxy_client_enabled,
)
from unique_web_search.services.proxy.mappers import map_search_response
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


@register_search_engine(
    name="brave",
    key=SearchEngineType.BRAVE,
    config_cls=BraveConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Brave Search",
)
class BraveSearch(SearchEngine[BraveConfig]):
    supports_proxy_search = True

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.is_configured = (
            search_proxy_client_enabled or get_brave_search_settings().is_configured
        )

    @override
    async def _proxy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        async with open_search_proxy_client(timeout=30.0) as client:
            response = await client.search.brave(
                query=query,
                fetch_size=self.config.fetch_size,
                extra_snippets=self.config.extra_snippets,
                spellcheck=self.config.spellcheck,
                text_decorations=self.config.text_decorations,
                operators=self.config.operators,
                ui_lang=self.config.ui_lang,
                units=self.config.units,
                summary=self.config.summary,
                include_fetch_metadata=self.config.include_fetch_metadata,
                goggles=self.config.goggles,
                country=self.config.country.value,
                freshness=self.config.freshness.value,
                search_lang=self.config.search_lang.value,
                safesearch=self.config.safesearch.value,
                result_filter=self.config.result_filter.value,
            )
            return map_search_response(response)

    @override
    async def _legacy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        raise NotImplementedError("Brave search is not supported in the legacy mode")
