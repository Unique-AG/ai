"""Pydantic models for Brave Search API request parameters and responses.

Covers both the Web Search (/v1/web/search) and News Search (/v1/news/search)
endpoints. Based on:
  - https://api-dashboard.search.brave.com/api-reference/web/search/get
  - https://api-dashboard.search.brave.com/api-reference/news/news_search/get
"""

from enum import StrEnum  # noqa: I001
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------


class SafeSearch(StrEnum):
    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"


class Freshness(StrEnum):
    """Predefined freshness shortcuts. Custom date ranges (YYYY-MM-DDtoYYYY-MM-DD) are also accepted as raw strings."""

    PAST_DAY = "pd"
    PAST_WEEK = "pw"
    PAST_MONTH = "pm"
    PAST_YEAR = "py"


class Units(StrEnum):
    METRIC = "metric"
    IMPERIAL = "imperial"


# ---------------------------------------------------------------------------
# Web Search – Request Parameters
# ---------------------------------------------------------------------------


class BraveWebSearchParams(BaseModel):
    """Query parameters for ``GET /v1/web/search``."""

    model_config = ConfigDict(populate_by_name=True)

    q: str = Field(
        ..., max_length=400, description="Search query (max 400 chars, 50 words)."
    )
    country: str = Field(
        default="US", description="2-char country code for result origin."
    )
    search_lang: str = Field(
        default="en", description="2+ char language code for results."
    )
    ui_lang: str = Field(default="en-US", description="UI language, e.g. 'en-US'.")
    count: int = Field(
        default=20, ge=1, le=20, description="Number of web results (max 20)."
    )
    offset: int = Field(
        default=0, ge=0, le=9, description="Zero-based page offset (max 9)."
    )
    safesearch: SafeSearch = Field(default=SafeSearch.MODERATE)
    freshness: str | None = Field(
        default=None, description="Time filter: pd/pw/pm/py or YYYY-MM-DDtoYYYY-MM-DD."
    )
    text_decorations: bool = Field(
        default=True, description="Include highlight markers in snippets."
    )
    spellcheck: bool = Field(default=True)
    result_filter: str | None = Field(
        default=None, description="Comma-separated result types to include."
    )
    goggles: str | None = Field(
        default=None, description="Goggle URL or inline definition for custom ranking."
    )
    units: Units | None = Field(default=None)
    extra_snippets: bool | None = Field(
        default=None, description="Return up to 5 extra snippets per result."
    )
    summary: bool | None = Field(
        default=None, description="Enable summarizer key generation."
    )
    enable_rich_callback: bool = Field(
        default=False, description="Enable rich 3rd-party data callback."
    )
    include_fetch_metadata: bool = Field(
        default=False, description="Include fetched_content_timestamp on results."
    )
    operators: bool = Field(default=True, description="Apply search operators.")


class BraveWebSearchHeaders(BaseModel):
    """Optional HTTP headers for location-aware web search requests."""

    x_loc_lat: float | None = Field(
        default=None, ge=-90.0, le=90.0, description="Client latitude."
    )
    x_loc_long: float | None = Field(
        default=None, ge=-180.0, le=180.0, description="Client longitude."
    )
    x_loc_timezone: str | None = Field(
        default=None, description="IANA timezone, e.g. 'America/New_York'."
    )
    x_loc_city: str | None = Field(default=None)
    x_loc_state: str | None = Field(
        default=None, description="ISO 3166-2 state/region code."
    )
    x_loc_state_name: str | None = Field(
        default=None, description="Full state/region name."
    )
    x_loc_country: str | None = Field(
        default=None, description="2-letter country code."
    )
    x_loc_postal_code: str | None = Field(default=None)
    api_version: str | None = Field(
        default=None, description="API version in YYYY-MM-DD format."
    )
    user_agent: str | None = Field(default=None)
    cache_control: str | None = Field(
        default=None, description="Set to 'no-cache' to bypass cache."
    )

    def to_headers(self) -> dict[str, str]:
        mapping: dict[str, str] = {
            "x_loc_lat": "X-Loc-Lat",
            "x_loc_long": "X-Loc-Long",
            "x_loc_timezone": "X-Loc-Timezone",
            "x_loc_city": "X-Loc-City",
            "x_loc_state": "X-Loc-State",
            "x_loc_state_name": "X-Loc-State-Name",
            "x_loc_country": "X-Loc-Country",
            "x_loc_postal_code": "X-Loc-Postal-Code",
            "api_version": "Api-Version",
            "user_agent": "User-Agent",
            "cache_control": "Cache-Control",
        }
        headers: dict[str, str] = {}
        for attr, header_name in mapping.items():
            value = getattr(self, attr)
            if value is not None:
                headers[header_name] = str(value)
        return headers


# ---------------------------------------------------------------------------
# News Search – Request Parameters
# ---------------------------------------------------------------------------


class BraveNewsSearchParams(BaseModel):
    """Query parameters for ``GET /v1/news/search``."""

    model_config = ConfigDict(populate_by_name=True)

    q: str = Field(
        ..., max_length=400, description="Search query (max 400 chars, 50 words)."
    )
    country: str = Field(
        default="US", description="2-char country code or 'ALL' for worldwide."
    )
    search_lang: str = Field(
        default="en", description="2+ char language code for results."
    )
    ui_lang: str = Field(default="en-US", description="UI language, e.g. 'en-US'.")
    count: int = Field(
        default=20, ge=1, le=50, description="Number of news results (max 50)."
    )
    offset: int = Field(
        default=0, ge=0, le=9, description="Zero-based page offset (max 9)."
    )
    safesearch: SafeSearch = Field(default=SafeSearch.STRICT)
    freshness: str | None = Field(
        default=None, description="Time filter: pd/pw/pm/py or YYYY-MM-DDtoYYYY-MM-DD."
    )
    spellcheck: bool = Field(default=True)
    extra_snippets: bool | None = Field(
        default=None, description="Return up to 5 extra snippets per result."
    )
    goggles: str | None = Field(
        default=None, description="Goggle URL or inline definition for custom ranking."
    )
    include_fetch_metadata: bool = Field(
        default=False, description="Include fetch timestamps in results."
    )
    operators: bool = Field(default=True, description="Apply search operators.")


# ---------------------------------------------------------------------------
# Shared response components
# ---------------------------------------------------------------------------

_RESPONSE_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


class BraveSearchOperators(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    applied: bool | None = None
    cleaned_query: str | None = None
    sites: list[str] | None = None


class BraveQuery(BaseModel):
    """The ``query`` object present in both web and news search responses."""

    model_config = _RESPONSE_MODEL_CONFIG

    original: str | None = None
    altered: str | None = None
    cleaned: str | None = None
    spellcheck_off: bool | None = None
    more_results_available: bool | None = None
    show_strict_warning: bool | None = None
    search_operators: BraveSearchOperators | None = None


class BraveMetaUrl(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    scheme: str | None = None
    netloc: str | None = None
    hostname: str | None = None
    favicon: str | None = None
    path: str | None = None


class BraveThumbnail(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    src: str | None = None
    original: str | None = None
    logo: bool | None = None


class BraveProfile(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    name: str | None = None
    url: str | None = None
    long_name: str | None = None
    img: str | None = None


# ---------------------------------------------------------------------------
# Web Search – Response models
# ---------------------------------------------------------------------------


class BraveWebResult(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    title: str
    url: str
    description: str | None = None
    age: str | None = None
    page_age: str | None = None
    language: str | None = None
    meta_url: BraveMetaUrl | None = None
    thumbnail: BraveThumbnail | None = None
    profile: BraveProfile | None = None
    extra_snippets: list[str] | None = None
    content_type: str | None = None
    family_friendly: bool | None = None
    is_source_local: bool | None = None
    is_source_both: bool | None = None
    fetched_content_timestamp: int | None = None

    deep_results: dict | None = None
    schemas: list[dict] | None = None
    product: dict | None = None
    recipe: dict | None = None
    article: dict | None = None
    book: dict | None = None
    software: dict | None = None
    rating: dict | None = None
    faq: dict | None = None
    movie: dict | None = None
    video: dict | None = None
    location: dict | None = None
    qa: dict | None = None
    creative_work: dict | None = None
    music_recording: dict | None = None
    organization: dict | None = None
    review: dict | None = None


class BraveWebResults(BaseModel):
    """Container for the ``web`` key in the search response."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[BraveWebResult] = Field(default_factory=list)
    mutated_by_goggles: bool | None = None
    family_friendly: bool | None = None


class BraveNewsResult(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    title: str
    url: str
    description: str | None = None
    age: str | None = None
    page_age: str | None = None
    page_fetched: str | None = None
    meta_url: BraveMetaUrl | None = None
    thumbnail: BraveThumbnail | None = None
    extra_snippets: list[str] | None = None
    fetched_content_timestamp: int | None = None


class BraveNewsResults(BaseModel):
    """Container for the ``news`` key in the web search response."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[BraveNewsResult] = Field(default_factory=list)


class BraveVideoResult(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    title: str | None = None
    url: str | None = None
    description: str | None = None
    age: str | None = None
    page_age: str | None = None
    meta_url: BraveMetaUrl | None = None
    thumbnail: BraveThumbnail | None = None


class BraveVideoResults(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[BraveVideoResult] = Field(default_factory=list)
    mutated_by_goggles: bool | None = None


class BraveResultReference(BaseModel):
    """A reference inside the ``mixed`` ordering object."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    index: int | None = None
    all: bool | None = None


class BraveMixed(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    main: list[BraveResultReference] = Field(default_factory=list)
    top: list[BraveResultReference] = Field(default_factory=list)
    side: list[BraveResultReference] = Field(default_factory=list)


class BraveRichHint(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    vertical: str | None = None
    callback_key: str | None = None


class BraveRich(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    hint: BraveRichHint | None = None


class BraveDiscussionData(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    forum_name: str | None = None
    num_answers: int | None = None
    question: str | None = None
    top_comment: str | None = None


class BraveDiscussionResult(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    title: str | None = None
    url: str | None = None
    description: str | None = None
    age: str | None = None
    data: BraveDiscussionData | None = None


class BraveDiscussions(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[BraveDiscussionResult] = Field(default_factory=list)
    mutated_by_goggles: bool | None = None


class BraveFaqResult(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    title: str | None = None
    url: str | None = None
    question: str | None = None
    answer: str | None = None


class BraveFaq(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[BraveFaqResult] = Field(default_factory=list)


class BraveInfobox(BaseModel):
    """Aggregated information on an entity shown as an infobox."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[dict] = Field(default_factory=list)


class BraveLocations(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    results: list[dict] = Field(default_factory=list)


class BraveSummarizer(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    key: str | None = None


# ---------------------------------------------------------------------------
# Top-level response models
# ---------------------------------------------------------------------------


class BraveWebSearchResponse(BaseModel):
    """Full response from ``GET /v1/web/search``."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: Literal["search"] = "search"
    query: BraveQuery | None = None
    discussions: BraveDiscussions | None = None
    faq: BraveFaq | None = None
    infobox: BraveInfobox | None = None
    locations: BraveLocations | None = None
    mixed: BraveMixed | None = None
    news: BraveNewsResults | None = None
    videos: BraveVideoResults | None = None
    web: BraveWebResults | None = None
    summarizer: BraveSummarizer | None = None
    rich: BraveRich | None = None


class BraveNewsSearchResponse(BaseModel):
    """Full response from ``GET /v1/news/search``."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: Literal["news"] = "news"
    query: BraveQuery | None = None
    results: list[BraveNewsResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Error responses
# ---------------------------------------------------------------------------


class BraveErrorDetail(BaseModel):
    model_config = _RESPONSE_MODEL_CONFIG

    id: str | None = None
    status: int | None = None
    code: str | None = None
    detail: str | None = None
    meta: dict | None = None


class BraveErrorResponse(BaseModel):
    """Error response returned by Brave Search API (404, 422, 429)."""

    model_config = _RESPONSE_MODEL_CONFIG

    type: str | None = None
    error: BraveErrorDetail | None = None
    time: int | None = None
