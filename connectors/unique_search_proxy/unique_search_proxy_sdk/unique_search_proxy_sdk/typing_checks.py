"""Static typing checks for provider endpoint factories (checked by basedpyright)."""

from __future__ import annotations

from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles

from unique_search_proxy_sdk._typed_endpoints import GoogleSearchEndpoint
from unique_search_proxy_sdk.agent_search_client import AgentSearchClient
from unique_search_proxy_sdk.crawl_client import CrawlClient
from unique_search_proxy_sdk.search_client import SearchClient


async def _search_provider_kwargs(client: SearchClient) -> None:
    await client.google(query="unique ag", gl="ch", fetch_size=3)
    await client.brave(query="news", country="US", safesearch="strict")
    await client.perplexity(
        query="papers",
        search_recency_filter="month",
        max_tokens=1000,
    )
    # Unknown kwargs should fail static checking:
    # await client.google(query="x", unknown_field=True)


def _search_endpoint_types(client: SearchClient) -> None:
    google = client.google
    _: GoogleSearchEndpoint = google


async def _agent_provider_kwargs(client: AgentSearchClient) -> None:
    await client.bing(query="timeline", fetch_size=5)
    await client.vertexai(
        query="timeline",
        vertexai_model_name="gemini-3-flash-preview",
    )


async def _crawl_provider_kwargs(client: CrawlClient) -> None:
    await client.basic(
        urls=["https://example.com"],
        content_types=ContentTypeToggles(html=True),
    )
    await client.tavily(
        urls=["https://example.com"],
        extract_depth="advanced",
        query="rerank",
    )
    await client.jina(urls=["https://example.com"], return_format="markdown")
    await client.firecrawl(urls=["https://example.com"], proxy="auto")


__all__ = [
    "_agent_provider_kwargs",
    "_crawl_provider_kwargs",
    "_search_endpoint_types",
    "_search_provider_kwargs",
]
