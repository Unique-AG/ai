from typing import Annotated, Any, TypeAlias, override

from pydantic import BaseModel, Field
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.firecrawl import (
    schema as firecrawl_schema,
)
from unique_toolkit._common.pydantic_helpers import NoneToDefault

from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

# The proxy waits ``timeout`` plus its own margin for Firecrawl; wait longer
# than that so the proxy's timeout error arrives instead of a dropped call.
_PROXY_CLIENT_TIMEOUT_MARGIN_SECONDS = 10.0


PreviewCharsOrNone: TypeAlias = (
    Annotated[int, Field(title="Characters", ge=50)]
    | Annotated[None, Field(title="Whole preview", description="None")]
)


class _RequiresScraping(BaseModel):
    # The admin form stores requires_scraping as null after an engine switch.
    # NoneToDefault reads null as False; json_schema_extra lets the form accept it.
    requires_scraping: Annotated[bool, NoneToDefault] = Field(
        default=False,
        title="Requires scraping",
        description=(
            "Read every search result and pass the full page content to the "
            "model instead of only the Firecrawl previews. Off by default: "
            "Firecrawl's previews follow the query, and in search mode V3 the "
            "model reads the pages it needs with the Web Page Reader whatever "
            "this is set to. The settings from here to 'Preview length on "
            "read pages' only apply when this is on."
        ),
        json_schema_extra={"type": ["boolean", "null"]},
    )


class FirecrawlSearchConfig(
    firecrawl_schema.FirecrawlInSearchScrapeOptions,
    _RequiresScraping,
    firecrawl_schema.FirecrawlSearchOptions,
):
    """Firecrawl search settings as the admin form shows them.

    The base order puts 'Requires scraping' after the search options and
    directly above the page-reading settings that depend on it.
    """

    repeated_preview_max_chars: PreviewCharsOrNone = Field(
        default=500,
        title="Preview length on read pages",
        description=(
            "Longest preview kept, in characters, for a result whose page was "
            "read. A read page is split into pieces and each piece repeats the "
            "preview, so a long preview multiplies. Results whose page was not "
            "read keep the whole preview, as does every result in search mode "
            "V3."
        ),
    )

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """Use the proxy's wire contract, excluding tool-only configuration fields."""
        return firecrawl_schema.FirecrawlSearchRequest

    @property
    def scrapes_inside_search(self) -> bool:
        """Whether Firecrawl itself reads the result pages during the search."""
        return self.requires_scraping and self.scrape_results

    def _merge_defaults(self) -> dict[str, Any]:
        # 'Requires scraping' is the one switch for reading result pages, as on
        # every other engine; without it Firecrawl must not read them either.
        defaults = super()._merge_defaults()
        defaults["scrape_results"] = self.scrapes_inside_search
        return defaults


@register_search_engine(
    name="firecrawl",
    key=SearchEngineType.FIRECRAWL,
    config_cls=FirecrawlSearchConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Firecrawl",
)
class FirecrawlSearch(SearchEngine[FirecrawlSearchConfig]):
    """Firecrawl search, served only through the Search Proxy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = search_proxy_client_enabled

    @property
    def requires_scraping(self) -> bool:
        """Whether the Web Page Reader still has to read the result pages."""
        return self.config.requires_scraping and not self.config.scrapes_inside_search

    @property
    def repeated_snippet_max_chars(self) -> int | None:
        return self.config.repeated_preview_max_chars

    @property
    def _standard_proxy_client_timeout(self) -> float:
        return float(self.config.timeout) + _PROXY_CLIENT_TIMEOUT_MARGIN_SECONDS

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        raise NotImplementedError(
            "Firecrawl search is not supported in the legacy mode"
        )
