from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.schema import DeactivatedNone

JinaReturnFormat = Literal["markdown", "html", "text", "screenshot", "pageshot"]
JinaEngine = Literal["auto", "browser", "direct", "cf-browser-rendering"]
JinaRetainImages = Literal["none", "all", "alt", "all_p", "alt_p"]

StrOrNone: TypeAlias = Annotated[str, Field(title="String")] | DeactivatedNone
PageTimeoutOrNone: TypeAlias = (
    Annotated[int, Field(title="Integer", ge=1, le=180)] | DeactivatedNone
)
CssSelectorListOrNone: TypeAlias = (
    Annotated[
        list[str],
        Field(title="CSS Selectors"),
        RJSFMetaTag({"ui:options": {"orderable": False}}),
    ]
    | DeactivatedNone
)
RetainImagesOrNone: TypeAlias = (
    Annotated[JinaRetainImages, Field(title="Retain Images")] | DeactivatedNone
)


class JinaConfig(BaseCrawlerConfig[CrawlerType.JINA]):
    """Deployment config for the Jina Reader crawler."""

    _request_model_name: ClassVar[str] = "JinaCrawlRequest"

    crawler: Annotated[
        Literal[CrawlerType.JINA], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=CrawlerType.JINA,
        title="Crawler",
        description="Provider discriminator; must be `Jina` for this config.",
    )

    return_format: JinaReturnFormat = Field(
        default="markdown",
        title="Return format",
        description=(
            "Jina Reader output format: `markdown`, `html`, `text`, `screenshot`, "
            "or `pageshot`."
        ),
    )
    engine: JinaEngine = Field(
        default="browser",
        title="Engine",
        description=(
            "`browser` for best quality, `direct` for speed, "
            "`cf-browser-rendering` for JS-heavy sites."
        ),
    )
    page_timeout: PageTimeoutOrNone = Field(
        default=None,
        title="Page load timeout",
        description=(
            "Max seconds to wait for the page to load (Jina Reader). "
            "Defaults to the crawl `timeout` when unset."
        ),
    )
    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=50,
        title="Maximum concurrent reader requests",
        description="Maximum concurrent Jina Reader POST requests.",
    )
    no_cache: bool = Field(
        default=False,
        title="Bypass cache",
        description="Bypass Jina cache and fetch fresh content.",
    )
    target_selector: CssSelectorListOrNone = Field(
        default=None,
        title="Target selector",
        description="CSS selectors to focus extraction on specific page elements.",
    )
    wait_for_selector: CssSelectorListOrNone = Field(
        default=None,
        title="Wait for selector",
        description="CSS selectors to wait for before returning content.",
    )
    remove_selector: CssSelectorListOrNone = Field(
        default=None,
        title="Remove selector",
        description="CSS selectors for page regions to strip (headers, footers, etc.).",
    )
    with_generated_alt: bool = Field(
        default=False,
        title="Generated alt text",
        description="Generate alt text for images missing alt tags.",
    )
    with_links_summary: bool = Field(
        default=False,
        title="Links summary",
        description="Include a links summary in the reader response.",
    )
    with_images_summary: bool = Field(
        default=False,
        title="Images summary",
        description="Include an images summary in the reader response.",
    )
    with_iframe: bool = Field(
        default=False,
        title="Include iframes",
        description="Include iframe content in the reader response.",
    )
    retain_images: RetainImagesOrNone = Field(
        default=None,
        title="Retain images",
        description="Control which images are retained in markdown output.",
    )
    locale: StrOrNone = Field(
        default=None,
        title="Locale",
        description="Browser locale used to render the page (e.g. `en-US`).",
    )
    referer: StrOrNone = Field(
        default=None,
        title="Referer",
        description="Referer header sent when fetching the target URL.",
    )
    proxy_url: StrOrNone = Field(
        default=None,
        title="Proxy URL",
        description="Proxy URL used by Jina Reader to access the target page.",
    )
    do_not_track: bool = Field(
        default=True,
        title="Do not track",
        description="Send DNT (Do Not Track) to the reader service.",
    )


JinaCrawlRequest = JinaConfig.request_model()


__all__ = [
    "JinaConfig",
    "JinaCrawlRequest",
    "JinaEngine",
    "JinaRetainImages",
    "JinaReturnFormat",
]
