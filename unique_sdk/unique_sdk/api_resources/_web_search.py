"""HTTP-API bindings for the public ``web-search-api`` endpoints.

These mirror the assistants-core ``unique-websearch`` CLI (search + crawl)
through the chat ``/public/web-search-api/{search,crawl,review}`` REST
surface, so SDK consumers get a typed, server-resolved engine/crawler
without touching ``unique_web_search`` directly. ``WebSearchReview`` asks
the user to approve a batch of queries before they are searched.

Two distinct resources are exposed because the two endpoints carry
different response envelopes (search returns ``{engine, query, results}``
with per-result ``url/title/snippet/content``; crawl returns ``{crawler,
results}`` with per-URL ``url/content/error``). Modelling them as separate
classes keeps the typed shape obvious at the call site and lets each one
register its own ``OBJECT_NAME`` for response routing.
"""

from typing import Any, Literal, TypedDict, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class WebSearchResultItem(TypedDict):
    """A single search hit returned by the configured search engine."""

    url: str
    title: str
    snippet: str
    # Empty string unless ``includeContent=True`` and the engine requires
    # scraping (or the engine itself returned page content).
    content: str


class WebSearch(APIResource["WebSearch"]):
    """``POST /web-search-api/search`` — query the configured search engine.

    Mirrors the assistants-core ``unique-websearch search`` CLI command.
    Engine selection follows the server's
    ``ACTIVE_SEARCH_ENGINES`` env config and may be overridden per request
    via ``searchEngineConfig``. ``includeContent=True`` triggers the
    server's crawler (configurable via ``crawlerConfig``) to populate
    ``result.content`` for engines that require scraping.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["web-search.search"]:
        return "web-search.search"

    class SearchParams(RequestOptions):
        query: str
        fetchSize: NotRequired[int | None]
        includeContent: NotRequired[bool | None]
        # Full discriminated-union payload passed straight through to the
        # server's WebSearchConfig.searchEngineConfig (e.g.
        # ``{"searchEngineName": "Google", ...}``).
        searchEngineConfig: NotRequired[dict[str, Any] | None]
        # Used only when includeContent=True and the engine needs scraping.
        crawlerConfig: NotRequired[dict[str, Any] | None]
        # Optional: when set, the space's Web Search toggle is enforced
        # server-side for this call. Omit for callers not acting on
        # behalf of a specific chat (unchanged legacy behavior).
        chatId: NotRequired[str | None]
        # Optional: the assistant message this call serves, for grouping
        # the call's activity records per turn. Send it only to a backend
        # that accepts it; older public APIs reject unknown body fields.
        messageId: NotRequired[str | None]
        # Required when the chat's space has query review on: the id of an
        # accepted review of this chat, and ``query`` must be one of the
        # queries the user approved. Omit when review is off or there is
        # no chat.
        reviewId: NotRequired[str | None]

    # Response envelope.
    engine: str
    query: str
    results: list[WebSearchResultItem]

    @classmethod
    def search(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["WebSearch.SearchParams"],
    ) -> "WebSearch":
        return cast(
            "WebSearch",
            cls._static_request(
                "post",
                "/web-search-api/search",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def search_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["WebSearch.SearchParams"],
    ) -> "WebSearch":
        return cast(
            "WebSearch",
            await cls._static_request_async(
                "post",
                "/web-search-api/search",
                user_id,
                company_id,
                params=params,
            ),
        )


class WebCrawlResultItem(TypedDict):
    """A single crawl outcome — content on success, error message on failure."""

    url: str
    content: str
    # Per-batch failure surfaces as a string here while ``content`` stays
    # an empty string; consumers can check truthiness of ``error`` to
    # distinguish a successful empty page from a failed crawl.
    error: str | None


class WebCrawl(APIResource["WebCrawl"]):
    """``POST /web-search-api/crawl`` — crawl URLs in parallel batches.

    Mirrors the assistants-core ``unique-websearch crawl`` CLI command.
    Crawler selection follows the server's ``ACTIVE_INHOUSE_CRAWLERS`` env
    config and may be overridden per request via ``crawlerConfig``.
    Per-batch crawl failures appear inline as ``{"error": <message>}``
    entries instead of aborting the whole call.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["web-search.crawl"]:
        return "web-search.crawl"

    class CrawlParams(RequestOptions):
        urls: list[str]
        parallel: NotRequired[int | None]
        crawlerConfig: NotRequired[dict[str, Any] | None]
        # Optional: when set, the space's Web Search toggle is enforced
        # server-side for this call. Omit for callers not acting on
        # behalf of a specific chat (unchanged legacy behavior).
        chatId: NotRequired[str | None]
        # Optional: the assistant message this call serves, for grouping
        # the call's activity records per turn. Send it only to a backend
        # that accepts it; older public APIs reject unknown body fields.
        messageId: NotRequired[str | None]

    # Response envelope.
    crawler: str
    results: list[WebCrawlResultItem]

    @classmethod
    def crawl(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["WebCrawl.CrawlParams"],
    ) -> "WebCrawl":
        return cast(
            "WebCrawl",
            cls._static_request(
                "post",
                "/web-search-api/crawl",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def crawl_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["WebCrawl.CrawlParams"],
    ) -> "WebCrawl":
        return cast(
            "WebCrawl",
            await cls._static_request_async(
                "post",
                "/web-search-api/crawl",
                user_id,
                company_id,
                params=params,
            ),
        )


WebSearchReviewStatus = Literal[
    "NOT_REQUIRED",
    "PENDING",
    "ACCEPTED",
    "DECLINED",
    "CANCELLED",
    "EXPIRED",
]


class WebSearchReview(APIResource["WebSearchReview"]):
    """``POST /web-search-api/review`` — ask the user to approve queries.

    One call covers the whole batch. ``NOT_REQUIRED`` means the space has
    query review off and the queries can be searched as sent. ``PENDING``
    means the form is in the chat; ``reviewId`` is also the elicitation id.
    ``ACCEPTED`` returns the queries the user approved, which may differ
    from the ones that were sent. ``DECLINED``, ``CANCELLED`` and
    ``EXPIRED`` return no queries and must not be searched. Sending the
    same queries again for the same message returns the same review.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["web-search.review"]:
        return "web-search.review"

    class ReviewParams(RequestOptions):
        chatId: str
        messageId: NotRequired[str | None]
        queries: list[str]

    # Response envelope.
    status: WebSearchReviewStatus
    reviewId: str | None
    queries: list[str]

    @classmethod
    def review(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["WebSearchReview.ReviewParams"],
    ) -> "WebSearchReview":
        """Request a review of ``queries`` for one chat message.

        Args:
            user_id (str): User the call is made as.
            company_id (str): Company the call is made in.
            **params: ``chatId``, optional ``messageId``, and ``queries``
                (1 to 20). ``messageId`` is required by the server when
                the space has query review on.

        Returns:
            WebSearchReview: The review status and, when accepted, the
            queries the user approved.
        """
        return cast(
            "WebSearchReview",
            cls._static_request(
                "post",
                "/web-search-api/review",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def review_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["WebSearchReview.ReviewParams"],
    ) -> "WebSearchReview":
        """Async form of :meth:`review`.

        Args:
            user_id (str): User the call is made as.
            company_id (str): Company the call is made in.
            **params: ``chatId``, optional ``messageId``, and ``queries``.

        Returns:
            WebSearchReview: The review status and, when accepted, the
            queries the user approved.
        """
        return cast(
            "WebSearchReview",
            await cls._static_request_async(
                "post",
                "/web-search-api/review",
                user_id,
                company_id,
                params=params,
            ),
        )
