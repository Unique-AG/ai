from typing import Annotated, override

from pydantic import BaseModel, Field
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.aws.schema import (
    AWS_MAX_QUERY_LENGTH,
    AwsConfig,
    AwsSearchRequest,
)
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_toolkit._common.pydantic_helpers import NoneToDefault

from unique_web_search.services.proxy.bridge import search_proxy_client_enabled
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.domain_policy import DomainPolicy
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import WebSearchResult


class AwsSearchConfig(AwsConfig):
    # The admin form stores requires_scraping as null after an engine switch.
    requires_scraping: Annotated[bool, NoneToDefault] = Field(
        default=False,
        title="Requires scraping",
        description=(
            "Crawl every search result. Off by default: AWS AgentCore already "
            "returns a text extract from its own index."
        ),
        json_schema_extra={"type": ["boolean", "null"]},
    )

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """Use the proxy's wire contract, excluding tool-only configuration fields."""
        return AwsSearchRequest


def trim_aws_query(query: str) -> str:
    """Shorten a query to the AgentCore limit, on a word boundary when possible."""
    text = query.strip()
    if len(text) <= AWS_MAX_QUERY_LENGTH:
        return text
    cut = text[:AWS_MAX_QUERY_LENGTH]
    if text[AWS_MAX_QUERY_LENGTH].isspace():
        return cut.rstrip()
    space = cut.rfind(" ")
    if space > 0:
        return cut[:space]
    return cut


@register_search_engine(
    name="aws",
    key=SearchEngineType.AWS,
    config_cls=AwsSearchConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="AWS AgentCore",
)
class AwsSearch(SearchEngine[AwsSearchConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = search_proxy_client_enabled

    @property
    def requires_scraping(self) -> bool:
        return getattr(self.config, "requires_scraping", False)

    @override
    def domain_policy(self) -> DomainPolicy:
        return DomainPolicy.of(
            include=self.config.include_domains,
            exclude=self.config.exclude_domains,
        )

    async def _standard_proxy_search(
        self,
        query: str,
        params: ExposedParams | None,
        engine: SearchEngineType,
    ) -> list[WebSearchResult]:
        return await super()._standard_proxy_search(
            trim_aws_query(query),
            params,
            engine,
        )

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        raise NotImplementedError("AWS search is not supported in the legacy mode")
