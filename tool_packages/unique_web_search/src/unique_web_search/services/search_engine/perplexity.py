import logging
from typing import Any, override

from perplexity import AsyncPerplexity
from perplexity.types.search_create_response import Result
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityConfig,
)

from unique_web_search.client_settings import get_perplexity_search_settings
from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

_LOGGER = logging.getLogger(__name__)
MAX_RESULTS_PER_REQUEST = 20


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
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        settings = get_perplexity_search_settings()
        assert settings.is_configured
        assert settings.api_key is not None

        overrides = (
            params.model_dump(by_alias=True, exclude_none=True) if params else {}
        )
        request = self.config.merge(overrides, query=query)
        provider_params = PerplexityConfig.provider_query_params(
            request,
            by_alias=False,
        )
        _apply_perplexity_api_rules(provider_params)

        async with async_client() as http_client:
            client = AsyncPerplexity(
                api_key=settings.api_key,
                http_client=http_client,
            )
            response = await client.search.create(
                query=query,
                max_results=min(request.fetch_size, MAX_RESULTS_PER_REQUEST),
                **provider_params,
            )

        return self._to_web_search_results(response.results)

    def _to_web_search_results(
        self,
        results: list[Result] | None,
    ) -> list[WebSearchResult]:
        if not results:
            _LOGGER.warning("No search results found in Perplexity search response")
            return []

        return [
            WebSearchResult(
                url=result.url,
                title=result.title,
                snippet=result.snippet or "No Snippet Found",
            )
            for result in results
        ]


def _apply_perplexity_api_rules(params: dict[str, Any]) -> None:
    """Apply constraints that the Perplexity Search API enforces."""
    if (
        params.get("max_tokens") is not None
        or params.get("max_tokens_per_page") is not None
    ):
        params.pop("search_context_size", None)
