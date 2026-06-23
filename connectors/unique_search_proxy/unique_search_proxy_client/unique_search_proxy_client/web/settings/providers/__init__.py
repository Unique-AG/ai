"""Upstream provider credentials (search engines, crawlers) loaded from environment."""

from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)
from unique_search_proxy_client.web.settings.providers.brave import (
    brave_search_credentials,
)
from unique_search_proxy_client.web.settings.providers.firecrawl import (
    firecrawl_crawl_credentials,
)
from unique_search_proxy_client.web.settings.providers.google import (
    google_search_credentials,
)
from unique_search_proxy_client.web.settings.providers.jina import (
    jina_crawl_credentials,
)
from unique_search_proxy_client.web.settings.providers.perplexity import (
    perplexity_search_credentials,
)
from unique_search_proxy_client.web.settings.providers.tavily import (
    tavily_crawl_credentials,
)
from unique_search_proxy_client.web.settings.providers.vertexai_agent import (
    vertexai_agent_credentials,
)

__all__ = [
    "bing_agent_credentials",
    "brave_search_credentials",
    "firecrawl_crawl_credentials",
    "google_search_credentials",
    "jina_crawl_credentials",
    "perplexity_search_credentials",
    "tavily_crawl_credentials",
    "vertexai_agent_credentials",
]
