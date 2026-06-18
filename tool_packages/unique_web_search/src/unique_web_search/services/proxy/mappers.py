from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from unique_search_proxy_sdk._generated.models.agent_search_response import (
    AgentSearchResponse,
)
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._generated.models.crawl_url_result import CrawlUrlResult
from unique_search_proxy_sdk._generated.models.per_url_error import PerUrlError
from unique_search_proxy_sdk._generated.models.search_response import SearchResponse

if TYPE_CHECKING:
    from unique_web_search.services.search_engine.schema import WebSearchResult
    from unique_web_search.services.search_engine.utils.grounding.response_parsing import (
        ResponseParser,
    )


def map_search_response(response: SearchResponse) -> list[WebSearchResult]:
    from unique_web_search.services.search_engine.schema import WebSearchResult

    return [
        WebSearchResult(
            url=result.url,
            title=result.title,
            snippet=result.snippet,
            content=result.content if isinstance(result.content, str) else "",
        )
        for result in response.curated
    ]


def result_to_markdown(result: CrawlUrlResult) -> str:
    if isinstance(result.content, str):
        return result.content

    if isinstance(result.error, PerUrlError):
        return f"Error: {result.error.message}"

    if isinstance(result.raw, str):
        return result.raw

    return "Error: No content returned by search proxy"


def map_crawl_response(response: CrawlResponse, urls: list[str]) -> list[str]:
    url_to_markdown = {
        result.url: result_to_markdown(result) for result in response.results
    }
    return [
        url_to_markdown.get(url, "Error: URL not found in search proxy response")
        for url in urls
    ]


async def map_agent_answer(
    answer: str,
    parsers: Sequence[ResponseParser],
) -> list[WebSearchResult]:
    from unique_web_search.services.search_engine.utils.grounding.response_parsing import (
        convert_response_to_search_results,
    )

    return await convert_response_to_search_results(answer, list(parsers))


def agent_answer_text(response: AgentSearchResponse) -> str:
    if isinstance(response.answer, str):
        return response.answer
    return ""
