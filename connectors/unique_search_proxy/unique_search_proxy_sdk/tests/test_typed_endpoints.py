import inspect

import pytest
from pydantic import BaseModel
from unique_search_proxy_core.crawlers.config_types import CRAWLER_NAME_TO_CONFIG
from unique_search_proxy_core.search_engines.config_types import (
    ENGINE_NAME_TO_CONFIG,
)

from unique_search_proxy_sdk import _typed_endpoints as typed

CRAWL_ENDPOINTS = {
    "Basic": typed.BasicCrawlEndpoint,
    "Firecrawl": typed.FirecrawlCrawlEndpoint,
    "Jina": typed.JinaCrawlEndpoint,
    "Tavily": typed.TavilyCrawlEndpoint,
}
SEARCH_ENDPOINTS = {
    "brave": typed.BraveSearchEndpoint,
    "custom_api": typed.CustomApiSearchEndpoint,
    "firecrawl": typed.FirecrawlSearchEndpoint,
    "google": typed.GoogleSearchEndpoint,
    "perplexity": typed.PerplexitySearchEndpoint,
}


def _keyword_names(endpoint: type) -> set[str]:
    return {
        name
        for name in inspect.signature(endpoint.__call__).parameters
        if name != "self"
    }


def _request_fields(config: type[BaseModel]) -> set[str]:
    request_model = getattr(config, "request_model", None)
    model = request_model() if callable(request_model) else config
    return set(model.model_fields)


@pytest.mark.ai
@pytest.mark.parametrize(("name", "endpoint"), CRAWL_ENDPOINTS.items())
def test_crawl_endpoint__accepts_every_request_field__for_each_crawler(
    name: str, endpoint: type
) -> None:
    config = next(c for key, c in CRAWLER_NAME_TO_CONFIG.items() if str(key) == name)

    assert _keyword_names(endpoint) == _request_fields(config)


@pytest.mark.ai
@pytest.mark.parametrize(("name", "endpoint"), SEARCH_ENDPOINTS.items())
def test_search_endpoint__accepts_every_request_field__for_each_engine(
    name: str, endpoint: type
) -> None:
    config = next(c for key, c in ENGINE_NAME_TO_CONFIG.items() if str(key) == name)

    assert _keyword_names(endpoint) == _request_fields(config)
