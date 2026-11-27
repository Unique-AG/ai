from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, TypeAlias

from pydantic import Field, model_validator
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.schema import DeactivatedNone

FirecrawlProxyMode = Literal["basic", "enhanced", "auto"]
FirecrawlPdfMode = Literal["auto", "fast", "ocr"]

MaxConcurrencyOrNone: TypeAlias = (
    Annotated[int, Field(title="Integer", ge=1)] | DeactivatedNone
)
TagListOrNone: TypeAlias = (
    Annotated[
        list[str],
        Field(title="Tags"),
        RJSFMetaTag({"ui:options": {"orderable": False}}),
    ]
    | DeactivatedNone
)
ScrapeHeadersOrNone: TypeAlias = (
    Annotated[dict[str, str], Field(title="Headers")] | DeactivatedNone
)
MaxAgeOrNone: TypeAlias = Annotated[int, Field(title="Integer", ge=0)] | DeactivatedNone
CountryOrNone: TypeAlias = (
    Annotated[str, Field(title="Country code", pattern=r"^[A-Z]{2}$")]
    | Annotated[None, Field(title="Firecrawl default (US)", description="None")]
)
LanguageListOrNone: TypeAlias = (
    Annotated[
        list[str],
        Field(title="Languages"),
        RJSFMetaTag({"ui:options": {"orderable": False}}),
    ]
    | Annotated[None, Field(title="Language of the country", description="None")]
)

_MS_PER_SECOND = 1000
# Firecrawl silently caps the cache age at seven days.
FIRECRAWL_MAX_CACHE_AGE_SECONDS = 7 * 24 * 60 * 60
MaxCacheAgeSecondsOrNone: TypeAlias = (
    Annotated[
        int,
        Field(title="Seconds", ge=0, le=FIRECRAWL_MAX_CACHE_AGE_SECONDS),
    ]
    | Annotated[None, Field(title="Firecrawl default (2 days)", description="None")]
)

# Firecrawl's own ceiling for ``maxPages``.
FIRECRAWL_MAX_PDF_PAGES = 10_000
MaxPdfPagesOrNone: TypeAlias = (
    Annotated[int, Field(title="Pages", ge=1, le=FIRECRAWL_MAX_PDF_PAGES)]
    | Annotated[None, Field(title="No limit", description="None")]
)


class FirecrawlConfig(BaseCrawlerConfig[CrawlerType.FIRECRAWL]):
    """Deployment config for Firecrawl (scrape or batch scrape)."""

    _request_model_name: ClassVar[str] = "FirecrawlCrawlRequest"

    crawler: Annotated[
        Literal[CrawlerType.FIRECRAWL], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=CrawlerType.FIRECRAWL,
        title="Crawler",
        description="Provider discriminator; must be `Firecrawl` for this config.",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        le=600,
        description=(
            "Request timeout in seconds. A page that is not in Firecrawl's "
            "cache takes 5 to 10 seconds, a long PDF longer."
        ),
    )

    only_main_content: bool = Field(
        default=True,
        title="Only main content",
        description="Exclude headers, navs, footers before markdown generation.",
    )
    only_clean_content: bool = Field(
        default=False,
        title="Only clean content",
        description="LLM pass to remove residual boilerplate from markdown.",
    )
    max_concurrency: MaxConcurrencyOrNone = Field(
        default=None,
        title="Max concurrency",
        description="Maximum concurrent scrapes for this batch job.",
    )
    ignore_invalid_urls: bool = Field(
        default=True,
        title="Ignore invalid URLs",
        description="Skip invalid URLs instead of failing the whole batch.",
    )
    wait_for: int = Field(
        default=0,
        ge=0,
        title="Wait for",
        description="Extra delay in milliseconds before fetching page content.",
    )
    mobile: bool = Field(
        default=False,
        title="Mobile emulation",
        description="Emulate a mobile device when scraping.",
    )
    block_ads: bool = Field(
        default=True,
        title="Block ads",
        description="Enable ad-blocking and cookie-popup blocking.",
    )
    remove_base64_images: bool = Field(
        default=True,
        title="Remove base64 images",
        description="Strip base64 image data from markdown output.",
    )
    proxy: FirecrawlProxyMode = Field(
        default="auto",
        title="Proxy mode",
        description=(
            "`auto` tries Firecrawl's basic proxies and retries with enhanced "
            "ones when a site blocks them. `basic` is fastest, `enhanced` is "
            "slower but gets past stronger bot protection. All cost the same."
        ),
    )
    include_tags: TagListOrNone = Field(
        default=None,
        title="Include tags",
        description="HTML tags to include in scrape output.",
    )
    exclude_tags: TagListOrNone = Field(
        default=None,
        title="Exclude tags",
        description="HTML tags to exclude from scrape output.",
    )
    scrape_headers: ScrapeHeadersOrNone = Field(
        default=None,
        title="Scrape headers",
        description="Headers sent to the target page (cookies, user-agent, etc.).",
    )
    max_cache_age_seconds: MaxCacheAgeSecondsOrNone = Field(
        default=600,
        title="Max cache age",
        description=(
            "How old Firecrawl's cached copy of a page may be, in seconds. The "
            "default of ten minutes keeps prices and news current. `0` always "
            "reads the page live, which is slower and fails more often. Cached "
            "copies cost the same credits but come back in under a second "
            "instead of 5 to 10."
        ),
    )
    store_in_cache: bool = Field(
        default=True,
        title="Store pages in Firecrawl's cache",
        description=(
            "Let Firecrawl keep the pages it reads in its cache and index for "
            "later requests. Turn off to keep them out; the request still "
            "shows in Firecrawl's activity log. Zero data retention goes "
            "further and stores nothing."
        ),
    )
    max_pdf_pages: MaxPdfPagesOrNone = Field(
        default=20,
        title="Max PDF pages to read",
        description=(
            "Read at most this many pages of each PDF. Each PDF page costs "
            "about 1 Firecrawl credit. The default of 20 is about what fits "
            "the default page length limit of 10,000 tokens, so more pages "
            "would be paid for and then cut."
        ),
    )
    pdf_mode: FirecrawlPdfMode = Field(
        default="auto",
        title="PDF reading mode",
        description=(
            "`auto` reads the embedded text and falls back to OCR. `fast` "
            "reads embedded text only. `ocr` runs OCR on every page."
        ),
    )
    country: CountryOrNone = Field(
        default=None,
        title="Country",
        description=(
            "ISO 3166-1 alpha-2 country code the pages are read from, for "
            "example `CH`. Firecrawl uses a proxy and the language and time "
            "zone of that country."
        ),
    )
    languages: LanguageListOrNone = Field(
        default=None,
        title="Languages",
        description=(
            "Preferred languages for the pages, most wanted first, for example "
            "`de-CH`. Sent together with the country; without one Firecrawl's "
            "default country `US` is used."
        ),
    )
    skip_tls_verification: bool = Field(
        default=False,
        title="Skip TLS verification",
        description="Read pages even when their TLS certificate is invalid.",
    )
    zero_data_retention: bool = Field(
        default=False,
        title="Zero data retention",
        description=(
            "Read pages with zero data retention even when the Search Proxy is "
            "deployed without it. It can never turn off what the deployment "
            "sets. Costs 1 extra Firecrawl credit per page. Firecrawl must "
            "have enabled it for the account, otherwise every read fails."
        ),
    )
    # Milliseconds; superseded by ``max_cache_age_seconds`` and kept so stored
    # configs that set it keep their cache age.
    max_age: Annotated[MaxAgeOrNone, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default=None,
        title="Max age (milliseconds)",
        description="Deprecated: use the max cache age in seconds.",
    )

    @model_validator(mode="before")
    @classmethod
    def _carry_over_legacy_max_age(cls, data: Any) -> Any:
        """Read a stored ``max_age`` as the cache age when the new field is absent.

        Without this the new field's default would replace the cache age such a
        config chose.
        """
        if not isinstance(data, dict):
            return data
        if "max_cache_age_seconds" in data or "maxCacheAgeSeconds" in data:
            return data
        legacy = data.get("max_age", data.get("maxAge"))
        if not isinstance(legacy, int) or isinstance(legacy, bool) or legacy < 0:
            return data
        seconds = min(legacy // _MS_PER_SECOND, FIRECRAWL_MAX_CACHE_AGE_SECONDS)
        return {**data, "max_cache_age_seconds": seconds}


FirecrawlCrawlRequest = FirecrawlConfig.request_model()


__all__ = [
    "FirecrawlConfig",
    "FirecrawlCrawlRequest",
    "FirecrawlPdfMode",
    "FirecrawlProxyMode",
    "FIRECRAWL_MAX_CACHE_AGE_SECONDS",
    "FIRECRAWL_MAX_PDF_PAGES",
    "MaxPdfPagesOrNone",
    "MaxCacheAgeSecondsOrNone",
]
