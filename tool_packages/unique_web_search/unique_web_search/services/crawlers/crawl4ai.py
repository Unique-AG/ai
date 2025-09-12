import logging
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field
from unique_toolkit.tools.config import get_configuration_dict

from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfig,
    CrawlerType,
)

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class DisplayMode(StrEnum):
    DETAILED = "DETAILED"
    AGGREGATED = "AGGREGATED"


class CacheMode(StrEnum):
    """
    Defines the caching behavior for web crawling operations.

    Modes:
    - ENABLED: Normal caching behavior (read and write)
    - DISABLED: No caching at all
    - READ_ONLY: Only read from cache, don't write
    - WRITE_ONLY: Only write to cache, don't read
    - BYPASS: Bypass cache for this operation
    """

    ENABLED = "enabled"
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    BYPASS = "bypass"


class MarkdownGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()
    options: dict[str, Any] = Field(
        default={
            "ignore_links": True,
            "ignore_emphasis": True,
            "ignore_images": True,
        },
        description="The options for the markdown generator",
    )


class RateLimiterConfig(BaseModel):
    model_config = get_configuration_dict()
    base_delay: tuple[float, float] = Field(
        default=(0.5, 1.0),
        description="The range for a random delay (in seconds) between consecutive requests to the same domain.",
    )
    max_delay: float = Field(
        default=1.0,
        description="The maximum allowable delay when rate-limiting errors occur",
    )
    max_retries: int = Field(
        default=0,
        description="The maximum number of retries to make when rate-limiting errors occur",
    )
    rate_limit_codes: list[int] = Field(
        default=[429, 503],
        description="The HTTP status codes that indicate rate-limiting errors",
    )


class CrawlerConfig(BaseModel):
    model_config = get_configuration_dict()
    cache_mode: CacheMode = Field(
        default=CacheMode.BYPASS,
        description="The cache mode",
    )
    scan_full_page: bool = Field(
        default=True,
        description="Whether to scan the full page",
    )
    wait_until: str = Field(
        default="domcontentloaded",
        description="The condition to wait for when navigating",
    )
    scroll_delay: float = Field(
        default=0.05,
        description="The delay to scroll the page",
    )
    remove_overlay_elements: bool = Field(
        default=True,
        description="Whether to remove the overlay elements",
    )
    simulate_user: bool = Field(
        default=True,
        description="Whether to simulate the user",
    )
    override_navigator: bool = Field(
        default=True,
        description="Whether to override the navigator",
    )


class PruningContentFilterConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=True,
        description="Whether to enable the content filter",
    )
    threshold: float = Field(
        default=0.5,
        description="The threshold for the content filter",
    )
    threshold_type: Literal["fixed", "dynamic"] = Field(
        default="fixed",
        description="The type of threshold",
    )
    min_word_threshold: int = Field(
        default=10,
        description="The minimum number of words to keep",
    )


class Crawl4AiCrawlerConfig(BaseCrawlerConfig[CrawlerType.CRAWL4AI]):
    crawler_type: Literal[CrawlerType.CRAWL4AI] = CrawlerType.CRAWL4AI

    max_concurrent_requests: int = Field(
        default=10,
        description="The maximum number of concurrent requests to make to the same domain.",
    )

    max_session_permit: int = Field(
        default=10,
        description="The maximum number of sessions to make to the same domain.",
    )
    markdown_generator_config: MarkdownGeneratorConfig = Field(
        default_factory=MarkdownGeneratorConfig,
        description="The markdown generator configuration",
    )

    rate_limiter_config: RateLimiterConfig = Field(
        default_factory=RateLimiterConfig,
        description="The rate limiter configuration",
    )

    crawler_config: CrawlerConfig = Field(
        default_factory=CrawlerConfig,
        description="The crawler configuration",
    )

    pruning_content_filter_config: PruningContentFilterConfig = Field(
        default_factory=PruningContentFilterConfig,
        description="The pruning content filter configuration",
    )


class Crawl4AiCrawler(BaseCrawler[Crawl4AiCrawlerConfig]):
    def __init__(self, config: Crawl4AiCrawlerConfig):
        super().__init__(config)

    # TODO: Find a solution for tracking
    # @track(
    #     tags=["crawl4ai", "scrape"],
    # )
    async def crawl(self, urls: list[str]) -> list[str]:
        # Lazy import of crawl4ai - only import when actually needed
        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
            CrawlResult,
            RateLimiter,
        )
        from crawl4ai.async_dispatcher import (
            SemaphoreDispatcher,
        )
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import (
            DefaultMarkdownGenerator,
        )

        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            verbose=False,
            text_mode=True,
        )

        content_filter = None
        if self.config.pruning_content_filter_config.enabled:
            content_filter = PruningContentFilter(
                threshold=self.config.pruning_content_filter_config.threshold,
                threshold_type=self.config.pruning_content_filter_config.threshold_type,
                min_word_threshold=self.config.pruning_content_filter_config.min_word_threshold,
            )

        markdown_generator = DefaultMarkdownGenerator(
            content_source="raw_html",
            content_filter=content_filter,
            options=self.config.markdown_generator_config.options,
        )

        # Convert string cache_mode to enum if needed
        cache_mode = CacheMode(self.config.crawler_config.cache_mode.value)

        run_config = CrawlerRunConfig(
            cache_mode=cache_mode,
            scan_full_page=self.config.crawler_config.scan_full_page,
            wait_until=self.config.crawler_config.wait_until,
            scroll_delay=self.config.crawler_config.scroll_delay,
            remove_overlay_elements=self.config.crawler_config.remove_overlay_elements,
            simulate_user=self.config.crawler_config.simulate_user,
            override_navigator=self.config.crawler_config.override_navigator,
            page_timeout=int(
                self.config.timeout * 1000  # Uses milliseconds as unit
            ),
            markdown_generator=markdown_generator,
        )

        rate_limiter = RateLimiter(
            base_delay=self.config.rate_limiter_config.base_delay,
            max_delay=self.config.rate_limiter_config.max_delay,
            max_retries=self.config.rate_limiter_config.max_retries,
            rate_limit_codes=self.config.rate_limiter_config.rate_limit_codes,
        )

        dispatcher = SemaphoreDispatcher(
            semaphore_count=self.config.max_concurrent_requests,
            max_session_permit=self.config.max_session_permit,
            rate_limiter=rate_limiter,
        )

        logger.info(f"Crawling {len(urls)} URLs with Crawl4AiCrawler")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler_results = await crawler.arun_many(
                urls, config=run_config, dispatcher=dispatcher
            )

        logger.info(
            f"Crawled {len(crawler_results)} URLs with Crawl4AiCrawler"  # type: ignore
        )

        def _get_markdown_from_crawl_result(crawl_result: CrawlResult) -> str:
            if crawl_result.success:
                try:
                    return str(crawl_result.markdown)
                except Exception as e:
                    logger.error(f"Failed to get markdown from crawl result: {e}")
                    return "Failed to get markdown from crawl result"
            else:
                return "Failed to Scrape"

        markdown_results = [
            _get_markdown_from_crawl_result(result)
            for result in crawler_results  # type: ignore
        ]

        return markdown_results
