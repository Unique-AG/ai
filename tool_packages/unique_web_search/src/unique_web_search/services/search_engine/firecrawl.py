from typing import Annotated, TypeAlias, override

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

PreviewCharsOrNone: TypeAlias = (
    Annotated[int, Field(title="Characters", ge=50)]
    | Annotated[None, Field(title="Whole preview", description="None")]
)


class FirecrawlSearchConfig(firecrawl_schema.FirecrawlSearchConfig):
    # The admin form stores requires_scraping as null after an engine switch.
    requires_scraping: Annotated[bool, NoneToDefault] = Field(
        default=False,
        title="Requires scraping",
        description=(
            "Read every search result with the Web Page Reader and pass the "
            "full page to the model. Off by default: Firecrawl's previews "
            "follow the query, and in search mode V3 the model reads the pages "
            "it needs whatever this is set to."
        ),
        json_schema_extra={"type": ["boolean", "null"]},
    )
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
        return getattr(self.config, "requires_scraping", False)

    @property
    def repeated_snippet_max_chars(self) -> int | None:
        return self.config.repeated_preview_max_chars

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        raise NotImplementedError(
            "Firecrawl search is not supported in the legacy mode"
        )
