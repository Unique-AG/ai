from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, overload

import humps
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.fields import ComputedFieldInfo, FieldInfo

ProxyRequestType = Literal["search", "agent_search", "crawl"]


def field_title_generator(
    title: str,
    info: FieldInfo | ComputedFieldInfo,
) -> str:
    return humps.decamelize(title).replace("_", " ").title()


def model_title_generator(model: type) -> str:
    return humps.decamelize(model.__name__).replace("_", " ").title()


def get_model_config(title: str | None = None) -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        field_title_generator=field_title_generator,
        model_title_generator=model_title_generator,
        populate_by_name=True,
        title=title,
    )


camelized_model_config = get_model_config()


# Marks the deactivated branch of an optional config value. Locally declared so
# core has no runtime dependency on unique-toolkit for this one-line alias.
DeactivatedNone = Annotated[
    None,
    Field(title="Deactivated", description="None"),
]


class ProxyErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FORBIDDEN_TARGET = "FORBIDDEN_TARGET"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    ENGINE_NOT_CONFIGURED = "ENGINE_NOT_CONFIGURED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    EMPTY_SEARCH_RESULTS = "EMPTY_SEARCH_RESULTS"


class ErrorDetail(BaseModel):
    model_config = camelized_model_config

    code: str
    message: str
    request: ProxyRequestType | None = None
    provider: str | None = None
    retryable: bool = False
    details: list[dict[str, Any]] | None = None
    raw: Any | None = Field(
        default=None,
        description=(
            "Upstream provider response on request-level failure "
            "(JSON object or text wrapper)"
        ),
    )


class ErrorResponse(BaseModel):
    model_config = camelized_model_config

    error: ErrorDetail


class WebSearchResult(BaseModel):
    """Normalized search result used on the curated response path."""

    model_config = camelized_model_config

    url: str
    title: str
    snippet: str = Field(
        ...,
        description="A short description of the content found on this website",
    )
    content: str = Field(
        default="",
        description="The content of the website",
    )


class WebSearchResults(BaseModel):
    model_config = camelized_model_config
    results: list[WebSearchResult] = Field(
        validation_alias=AliasChoices("results", "curated")
    )

    def __len__(self) -> int:
        return len(self.results)

    @overload
    def extend(self, other: WebSearchResults) -> WebSearchResults: ...
    @overload
    def extend(self, other: list[WebSearchResult]) -> WebSearchResults: ...

    def extend(
        self, other: WebSearchResults | list[WebSearchResult]
    ) -> WebSearchResults:
        if isinstance(other, WebSearchResults):
            return WebSearchResults(results=self.results + other.results)
        elif isinstance(other, list):
            return WebSearchResults(results=self.results + other)
        else:
            raise ValueError(f"Invalid type: {type(other)}")

    def dedupe(self) -> WebSearchResults:
        """Drop duplicate results with the same URL string."""
        seen: set[str] = set()
        deduped: list[WebSearchResult] = []
        for result in self.results:
            if result.url in seen:
                continue
            seen.add(result.url)
            deduped.append(result)
        return WebSearchResults(results=deduped)


class SearchEngineRaw(BaseModel):
    model_config = camelized_model_config
    pages: list[dict]

    def append(self, page: dict) -> None:
        self.pages.append(page)


class PerUrlError(BaseModel):
    model_config = camelized_model_config

    code: str
    message: str
    status_code: int | None = Field(
        default=None,
        description=(
            "Upstream HTTP status code for this URL when the failure was an HTTP "
            "error (e.g. 403, 404, 500 from the Basic crawler); null when no HTTP "
            "response was received (timeouts, transport, processing, blocked targets)"
        ),
    )


class CrawlUrlResult(BaseModel):
    model_config = camelized_model_config

    url: str
    content: str | None = Field(
        default=None,
        description="Markdown extracted from HTML responses; null when unprocessed",
    )
    content_type: str | None = Field(
        default=None,
        description="Response Content-Type (media type only, parameters stripped)",
    )
    error: PerUrlError | None = None
    raw: Any | None = Field(
        default=None,
        description=(
            "Upstream provider response for this URL (JSON object or text wrapper); "
            "included on success and on per-URL failures for debugging"
        ),
    )


class SearchResponse(BaseModel):
    model_config = camelized_model_config

    engine: str
    query: str
    raw: Any = Field(..., description="Opaque provider payload")
    curated: list[WebSearchResult]


class AnswerSpanCitation(BaseModel):
    """A source cited at a specific span of the answer text.

    Grounding with Bing Search reports these as ``url_citation`` annotations:
    the agent writes a marker such as ``【4:0†source】`` into its answer, and
    Foundry attaches the source to that marker's character span.
    """

    model_config = camelized_model_config

    url: str = Field(description="URL of the cited source")
    title: str | None = Field(
        default=None,
        description="Title of the cited source",
    )
    marker: str = Field(
        description="Answer text between start_index and end_index",
    )
    start_index: int = Field(
        description="Character offset in the answer where the marker starts",
    )
    end_index: int = Field(
        description="Character offset in the answer just past the marker",
    )
    output_item_id: str | None = Field(
        default=None,
        description="Output item the citation is attached to, if the provider reports one",
    )


class AgentSearchResponse(BaseModel):
    """Result of an agent-based (grounded) search.

    Thin egress contract: opaque ``answer`` text from the provider, the
    citations the provider attached to it, and ``raw`` for debugging. Consumers
    interpret ``answer`` (JSON parsing, mapping citations, etc.).
    """

    model_config = camelized_model_config

    engine: str
    query: str
    answer: str = Field(
        default="",
        description="Agent response text as returned by the provider (opaque to the proxy)",
    )
    citations: list[AnswerSpanCitation] = Field(
        default_factory=list,
        description=(
            "Sources cited in the answer. Only Grounding with Bing Search "
            "reports citations; other engines return an empty list."
        ),
    )
    raw: Any = Field(default=None, description="Opaque provider payload")


class AgentSearchDelta(BaseModel):
    """Incremental answer token emitted while streaming an agent search."""

    model_config = camelized_model_config

    type: Literal["delta"] = "delta"
    text: str


class AgentSearchDone(BaseModel):
    """Terminal streaming event carrying the fully assembled response."""

    model_config = camelized_model_config

    type: Literal["done"] = "done"
    response: AgentSearchResponse


AgentSearchStreamEvent = Annotated[
    AgentSearchDelta | AgentSearchDone,
    Field(discriminator="type"),
]


class ProvidersListResponse(BaseModel):
    model_config = camelized_model_config

    search_engines: list[str] = Field(
        ...,
        description="Registered search engine ids (config discriminator values)",
    )
    agent_engines: list[str] = Field(
        default_factory=list,
        description="Registered agent search engine ids (config discriminator values)",
    )
    crawlers: list[str] = Field(
        ...,
        description="Registered crawler ids (config discriminator values)",
    )


class CrawlResponse(BaseModel):
    model_config = camelized_model_config

    crawler: str
    results: list[CrawlUrlResult]


class CrawlerConfig(BaseModel):
    model_config = camelized_model_config

    crawler: str = Field(..., title="Crawler", description="Crawler identifier")
