"""Typed endpoint wrappers exposing core request-model kwargs to type checkers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Generic, Literal, TypeVar

from unique_search_proxy_core.agent_engines.base import DEFAULT_GENERATION_INSTRUCTIONS
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.crawlers.jina.schema import (
    JinaEngine,
    JinaRetainImages,
    JinaReturnFormat,
)
from unique_search_proxy_core.crawlers.tavily.schema import (
    TavilyExtractDepth,
    TavilyExtractFormat,
)
from unique_search_proxy_core.search_engines.brave.schema import (
    BraveSafesearch,
    BraveUnits,
)
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleSafeDefault,
    GoogleSiteSearchFilter,
)
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityRecencyFilter,
    PerplexitySearchContextSize,
)

from unique_search_proxy_sdk._generated.models.agent_search_response import (
    AgentSearchResponse,
)
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._generated.models.search_response import SearchResponse

ResponseT = TypeVar("ResponseT")


class _TypedPostEndpoint(Generic[ResponseT]):
    __slots__ = ("_call",)

    def __init__(self, call: Callable[..., Awaitable[ResponseT]]) -> None:
        self._call = call


class GoogleSearchEndpoint(_TypedPostEndpoint[SearchResponse]):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["google"] = "google",
        fetch_size: int = 10,
        timeout: int = 30,
        search_engine_id: str | None = None,
        safe: GoogleSafeDefault = "active",
        gl: str | None = None,
        hl: str | None = None,
        lr: str | None = None,
        date_restrict: str | None = None,
        exact_terms: str | None = None,
        exclude_terms: str | None = None,
        file_type: str | None = None,
        site_search: str | None = None,
        site_search_filter: GoogleSiteSearchFilter | None = None,
        sort: str | None = None,
    ) -> SearchResponse:
        return await self._call(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            search_engine_id=search_engine_id,
            safe=safe,
            gl=gl,
            hl=hl,
            lr=lr,
            date_restrict=date_restrict,
            exact_terms=exact_terms,
            exclude_terms=exclude_terms,
            file_type=file_type,
            site_search=site_search,
            site_search_filter=site_search_filter,
            sort=sort,
        )


class BraveSearchEndpoint(_TypedPostEndpoint[SearchResponse]):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["brave"] = "brave",
        fetch_size: int = 10,
        timeout: int = 30,
        extra_snippets: bool = True,
        spellcheck: bool = False,
        text_decorations: bool = True,
        operators: bool = True,
        ui_lang: str = "en-US",
        units: BraveUnits | None = None,
        summary: bool = True,
        include_fetch_metadata: bool = False,
        goggles: str | list[str] | None = None,
        country: str | None = None,
        freshness: str | None = None,
        search_lang: str | None = None,
        safesearch: BraveSafesearch | None = None,
        result_filter: list[str] | None = None,
    ) -> SearchResponse:
        return await self._call(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            extra_snippets=extra_snippets,
            spellcheck=spellcheck,
            text_decorations=text_decorations,
            operators=operators,
            ui_lang=ui_lang,
            units=units,
            summary=summary,
            include_fetch_metadata=include_fetch_metadata,
            goggles=goggles,
            country=country,
            freshness=freshness,
            search_lang=search_lang,
            safesearch=safesearch,
            result_filter=result_filter,
        )


class PerplexitySearchEndpoint(_TypedPostEndpoint[SearchResponse]):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["perplexity"] = "perplexity",
        fetch_size: int = 10,
        timeout: int = 30,
        max_tokens: int | None = None,
        max_tokens_per_page: int | None = None,
        country: str | None = None,
        search_context_size: PerplexitySearchContextSize | None = None,
        search_language_filter: list[str] | None = None,
        search_domain_filter: list[str] | None = None,
        search_recency_filter: PerplexityRecencyFilter | None = None,
        last_updated_after_filter: str | None = None,
        last_updated_before_filter: str | None = None,
        search_after_date_filter: str | None = None,
        search_before_date_filter: str | None = None,
    ) -> SearchResponse:
        return await self._call(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            max_tokens=max_tokens,
            max_tokens_per_page=max_tokens_per_page,
            country=country,
            search_context_size=search_context_size,
            search_language_filter=search_language_filter,
            search_domain_filter=search_domain_filter,
            search_recency_filter=search_recency_filter,
            last_updated_after_filter=last_updated_after_filter,
            last_updated_before_filter=last_updated_before_filter,
            search_after_date_filter=search_after_date_filter,
            search_before_date_filter=search_before_date_filter,
        )


class BingAgentSearchEndpoint(_TypedPostEndpoint[AgentSearchResponse]):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["bing"] = "bing",
        generation_instructions: str = DEFAULT_GENERATION_INSTRUCTIONS,
        timeout: int = 120,
        fetch_size: int = 5,
        agent_id: str | None = None,
    ) -> AgentSearchResponse:
        return await self._call(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            fetch_size=fetch_size,
            agent_id=agent_id,
        )


class VertexAIAgentSearchEndpoint(_TypedPostEndpoint[AgentSearchResponse]):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["vertexai"] = "vertexai",
        generation_instructions: str = DEFAULT_GENERATION_INSTRUCTIONS,
        timeout: int = 120,
        vertexai_model_name: str = "gemini-3-flash-preview",
        enable_enterprise_search: bool = False,
    ) -> AgentSearchResponse:
        return await self._call(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            vertexai_model_name=vertexai_model_name,
            enable_enterprise_search=enable_enterprise_search,
        )


class _TypedStreamEndpoint:
    __slots__ = ("_call",)

    def __init__(
        self,
        call: Callable[..., AsyncIterator[dict[str, Any]]],
    ) -> None:
        self._call = call


class BingAgentSearchStreamEndpoint(_TypedStreamEndpoint):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["bing"] = "bing",
        generation_instructions: str = DEFAULT_GENERATION_INSTRUCTIONS,
        timeout: int = 120,
        fetch_size: int = 5,
        agent_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        async for event in self._call(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            fetch_size=fetch_size,
            agent_id=agent_id,
        ):
            yield event


class VertexAIAgentSearchStreamEndpoint(_TypedStreamEndpoint):
    async def __call__(
        self,
        *,
        query: str,
        engine: Literal["vertexai"] = "vertexai",
        generation_instructions: str = DEFAULT_GENERATION_INSTRUCTIONS,
        timeout: int = 120,
        vertexai_model_name: str = "gemini-3-flash-preview",
        enable_enterprise_search: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        async for event in self._call(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            vertexai_model_name=vertexai_model_name,
            enable_enterprise_search=enable_enterprise_search,
        ):
            yield event


class BasicCrawlEndpoint(_TypedPostEndpoint[CrawlResponse]):
    async def __call__(
        self,
        *,
        urls: list[str],
        crawler: Literal["Basic"] = "Basic",
        timeout: int = 30,
        content_types: ContentTypeToggles = ContentTypeToggles(),
        max_concurrent_requests: int = 10,
    ) -> CrawlResponse:
        return await self._call(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            content_types=content_types,
            max_concurrent_requests=max_concurrent_requests,
        )


class TavilyCrawlEndpoint(_TypedPostEndpoint[CrawlResponse]):
    async def __call__(
        self,
        *,
        urls: list[str],
        crawler: Literal["Tavily"] = "Tavily",
        timeout: int = 30,
        extract_depth: TavilyExtractDepth = "advanced",
        format: TavilyExtractFormat = "markdown",
        query: str | None = None,
        chunks_per_source: int | None = None,
        include_images: bool = False,
        include_favicon: bool = False,
        include_usage: bool = False,
    ) -> CrawlResponse:
        return await self._call(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            extract_depth=extract_depth,
            format=format,
            query=query,
            chunks_per_source=chunks_per_source,
            include_images=include_images,
            include_favicon=include_favicon,
            include_usage=include_usage,
        )


class JinaCrawlEndpoint(_TypedPostEndpoint[CrawlResponse]):
    async def __call__(
        self,
        *,
        urls: list[str],
        crawler: Literal["Jina"] = "Jina",
        timeout: int = 30,
        return_format: JinaReturnFormat = "markdown",
        engine: JinaEngine = "browser",
        page_timeout: int | None = None,
        max_concurrent_requests: int = 10,
        no_cache: bool = False,
        target_selector: list[str] | None = None,
        wait_for_selector: list[str] | None = None,
        remove_selector: list[str] | None = None,
        with_generated_alt: bool = False,
        with_links_summary: bool = False,
        with_images_summary: bool = False,
        with_iframe: bool = False,
        retain_images: JinaRetainImages | None = None,
        locale: str | None = None,
        referer: str | None = None,
        proxy_url: str | None = None,
        do_not_track: bool = True,
    ) -> CrawlResponse:
        return await self._call(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            return_format=return_format,
            engine=engine,
            page_timeout=page_timeout,
            max_concurrent_requests=max_concurrent_requests,
            no_cache=no_cache,
            target_selector=target_selector,
            wait_for_selector=wait_for_selector,
            remove_selector=remove_selector,
            with_generated_alt=with_generated_alt,
            with_links_summary=with_links_summary,
            with_images_summary=with_images_summary,
            with_iframe=with_iframe,
            retain_images=retain_images,
            locale=locale,
            referer=referer,
            proxy_url=proxy_url,
            do_not_track=do_not_track,
        )


class FirecrawlCrawlEndpoint(_TypedPostEndpoint[CrawlResponse]):
    async def __call__(
        self,
        *,
        urls: list[str],
        crawler: Literal["Firecrawl"] = "Firecrawl",
        timeout: int = 30,
        only_main_content: bool = True,
        only_clean_content: bool = False,
        max_concurrency: int | None = None,
        ignore_invalid_urls: bool = True,
        wait_for: int = 0,
        mobile: bool = False,
        block_ads: bool = True,
        remove_base64_images: bool = True,
        proxy: Literal["basic", "enhanced", "auto"] = "auto",
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        scrape_headers: dict[str, str] | None = None,
        max_age: int | None = None,
    ) -> CrawlResponse:
        return await self._call(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            only_main_content=only_main_content,
            only_clean_content=only_clean_content,
            max_concurrency=max_concurrency,
            ignore_invalid_urls=ignore_invalid_urls,
            wait_for=wait_for,
            mobile=mobile,
            block_ads=block_ads,
            remove_base64_images=remove_base64_images,
            proxy=proxy,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            scrape_headers=scrape_headers,
            max_age=max_age,
        )


__all__ = [
    "BasicCrawlEndpoint",
    "BingAgentSearchEndpoint",
    "BingAgentSearchStreamEndpoint",
    "BraveSearchEndpoint",
    "FirecrawlCrawlEndpoint",
    "GoogleSearchEndpoint",
    "JinaCrawlEndpoint",
    "PerplexitySearchEndpoint",
    "TavilyCrawlEndpoint",
    "VertexAIAgentSearchEndpoint",
    "VertexAIAgentSearchStreamEndpoint",
]
