from typing import Any, override

from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityConfig,
)

from unique_web_search.client_settings import get_perplexity_search_settings
from unique_web_search.services.proxy.bridge import search_proxy_client_enabled
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
    config_display_name="Perplexity",
)
class PerplexitySearch(SearchEngine[PerplexityConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = (
            search_proxy_client_enabled
            or get_perplexity_search_settings().is_configured
        )

    @override
    async def _legacy_search(
        self,
        query: str,
        params: dict[str, Any],
    ) -> list[WebSearchResult]:
        raise NotImplementedError(
            "Perplexity search is not supported in the legacy mode"
        )
