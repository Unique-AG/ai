from typing import Annotated, override

from pydantic import BaseModel, Field
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityConfig,
    PerplexitySearchRequest,
)
from unique_toolkit._common.pydantic_helpers import NoneToDefault

from unique_web_search.client_settings import get_perplexity_search_settings
from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


class PerplexitySearchConfig(PerplexityConfig):
    # The admin form stores null here when a space switches to Perplexity from
    # an engine that has this field, so null must load as off and pass the
    # form's validation.
    requires_scraping: Annotated[bool, NoneToDefault] = Field(
        default=False,
        title="Requires scraping",
        description=(
            "Crawl every search result and pass the full page content to the "
            "model instead of only the Perplexity excerpts."
        ),
        json_schema_extra={"type": ["boolean", "null"]},
    )

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """Use the proxy's wire contract, excluding tool-only configuration fields."""
        return PerplexitySearchRequest


@register_search_engine(
    name="perplexity",
    key=SearchEngineType.PERPLEXITY,
    config_cls=PerplexitySearchConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Perplexity",
)
class PerplexitySearch(SearchEngine[PerplexitySearchConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = (
            search_proxy_client_enabled
            or get_perplexity_search_settings().is_configured
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
        raise NotImplementedError(
            "Perplexity search is not supported in the legacy mode"
        )
