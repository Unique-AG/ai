import asyncio
import logging

from unique_toolkit._common.execution import SafeTaskExecutor
from unique_toolkit.language_model import LanguageModelService, TypeDecoder, TypeEncoder

from unique_web_search.services.content_processing.cleaning import (
    LineRemoval,
    MarkdownTransform,
)
from unique_web_search.services.content_processing.config import (
    ContentProcessorConfig,
)
from unique_web_search.services.content_processing.processing_strategies.base import (
    CleaningStrategy,
    ProcessingStrategy,
)
from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcess,
)
from unique_web_search.services.content_processing.processing_strategies.truncate import (
    Truncate,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.utils import WebPageChunk

_LOGGER = logging.getLogger(__name__)


class ContentProcessor:
    def __init__(
        self,
        language_model_service: LanguageModelService,
        config: ContentProcessorConfig,
        encoder: TypeEncoder,
        decoder: TypeDecoder,
    ):
        self.config = config
        self.language_model_service = language_model_service
        self._encoder = encoder
        self._decoder = decoder

        self._cleaning_strategies: list[CleaningStrategy] = [
            LineRemoval(
                config=self.config.cleaning.line_removal,
            ),
            MarkdownTransform(
                enabled=self.config.cleaning.enable_markdown_cleaning,
            ),
        ]

        self._processing_strategies: list[ProcessingStrategy] = [
            Truncate(
                config=self.config.processing_strategies.truncate,
                encoder=encoder,
                decoder=decoder,
            ),
            LLMProcess(
                config=self.config.processing_strategies.llm_processor,
                llm_service=self.language_model_service,
                encoder=encoder,
                decoder=decoder,
            ),
        ]

    async def run(self, query: str, pages: list[WebSearchResult]) -> list[WebPageChunk]:
        """
        Preprocess the pages content.
        Args:
            pages: list of pages.
        Returns:
            list[WebPageChunk]: List of processed webpage chunks.
        """

        ## Clean content
        pages = [self._clean_content(page) for page in pages]

        ## Apply Processing Strategies
        processed_pages = await self._process_pages(query, pages)

        ## Split pages to chunks
        pages_chunks = self._split_pages_to_chunks(processed_pages)

        _LOGGER.info(f"Number of chunks total: {len(pages_chunks)}")

        return pages_chunks

    def _clean_content(self, page: WebSearchResult) -> WebSearchResult:
        active_cleaning_strategies = [
            strategy.__class__.__name__
            for strategy in self._cleaning_strategies
            if strategy.is_enabled
        ]
        _LOGGER.info(f"Cleaning content with strategies: {active_cleaning_strategies}")
        for strategy in self._cleaning_strategies:
            if strategy.is_enabled:
                page.content = strategy(page.content)
        return page

    async def _process_pages(
        self, query: str, pages: list[WebSearchResult]
    ) -> list[WebSearchResult]:
        # Apply processing strategy with regex preprocessing as baseline
        active_strategies = [
            strategy.__class__.__name__
            for strategy in self._processing_strategies
            if strategy.is_enabled
        ]

        _LOGGER.info(f"Processing pages with strategies: {active_strategies}")

        async def process_single_page(page: WebSearchResult) -> WebSearchResult:
            for strategy in self._processing_strategies:
                if strategy.is_enabled:
                    page = await strategy(page=page, query=query)
            return page

        safe_task_executor = SafeTaskExecutor(logger=_LOGGER)

        results = await asyncio.gather(
            *[
                safe_task_executor.execute_async(
                    process_single_page,
                    page=page,
                )
                for page in pages
            ],
        )

        processed_pages = []
        for result, page in zip(results, pages):
            if result.success:
                processed_page = result.unpack()
            else:
                # Empty content to avoid overfilling the context in case processing strategy fails
                _LOGGER.error(
                    f"Processing strategy failed for page {page.url}: {result.exception}",
                    exc_info=result.exception,
                )
                processed_page.content = ""
            processed_pages.append(page)

        return processed_pages

    def _split_pages_to_chunks(
        self, pages: list[WebSearchResult]
    ) -> list[WebPageChunk]:
        """Build a vector store for the pages.
        Args:
            pages: list of pages.
        Returns:
            pd.DataFrame: DataFrame with the pages.
        """
        records = [
            record
            for chunks_records in map(self._create_chunks, pages)
            for record in chunks_records
        ]
        return records

    def _create_chunks(self, page: WebSearchResult) -> list[WebPageChunk]:
        """
        Create chunks from the page content.
        Args:
            page: dict with the page content.
        Returns:
            list[dict]: list of chunks.
        """

        def even_split(text: str, chunk_size: int) -> list[str]:
            tokens = self._encoder(text)
            return [
                self._decoder(tokens[i : i + chunk_size])
                for i in range(0, len(tokens), chunk_size)
            ]

        chunks = even_split(page.content, self.config.chunk_size)

        if len(chunks) == 0:
            return [
                WebPageChunk(
                    url=page.url,
                    display_link=page.display_link,
                    title=page.title,
                    snippet=page.snippet,
                    content=self._wrap_with_snippet(page.snippet, page.content),
                    order="0",
                )
            ]

        records = [
            WebPageChunk(
                url=page.url,
                display_link=page.display_link,
                title=page.title,
                snippet=page.snippet,
                content=self._wrap_with_snippet(page.snippet, chunk),
                order=str(order),
            )
            for order, chunk in enumerate(chunks)
        ]
        return records

    @staticmethod
    def _wrap_with_snippet(snippet: str, content: str) -> str:
        if len(content) > 0:
            return f"<SearchEngineSnippet>{snippet}</SearchEngineSnippet>\n\n<FetchContent>{content}</FetchContent>"
        return f"<SearchEngineSnippet>{snippet}</SearchEngineSnippet>"
