from typing import override

from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityConfig,
)

from unique_web_search.client_settings import get_perplexity_search_settings
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
    name="perplexity",
    key=SearchEngineType.PERPLEXITY,
    config_cls=PerplexityConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Perplexity Search",
)
class PerplexitySearch(SearchEngine[PerplexityConfig]):
    supports_proxy_search = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = (
            search_proxy_client_enabled
            or get_perplexity_search_settings().is_configured
        )

    @override
    async def _proxy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        async with open_search_proxy_client(timeout=30.0) as client:
            response = await client.search.perplexity(
                query=query,
                fetch_size=self.config.fetch_size,
                max_tokens=self.config.max_tokens,
                max_tokens_per_page=self.config.max_tokens_per_page,
                country=self.config.country.value,
                search_context_size=self.config.search_context_size.value,
                search_language_filter=self.config.search_language_filter.value,
                search_domain_filter=self.config.search_domain_filter.value,
                search_recency_filter=self.config.search_recency_filter.value,
                last_updated_after_filter=self.config.last_updated_after_filter.value,
                last_updated_before_filter=self.config.last_updated_before_filter.value,
                search_after_date_filter=self.config.search_after_date_filter.value,
                search_before_date_filter=self.config.search_before_date_filter.value,
            )
            return map_search_response(response)

    @override
    async def _legacy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        raise NotImplementedError(
            "Perplexity search is not supported in the legacy mode"
        )
