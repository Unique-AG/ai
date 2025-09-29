import asyncio
import logging
import re

import tiktoken
from langchain.text_splitter import TokenTextSplitter
from openai.types.chat import ChatCompletionMessageParam
from unique_toolkit.agentic.tools.utils.execution.execution import SafeTaskExecutor
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.embedding.service import EmbeddingService
from unique_toolkit.framework_utilities.openai import get_async_openai_client
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_web_search.services.content_processing.config import (
    REGEX_CONTENT_TRANSFORMATIONS,
    ContentProcessingStartegy,
    ContentProcessorConfig,
    WebPageChunk,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = logging.getLogger(__name__)


DEFAULT_ENCODER_MODEL = "cl100k_base"


class ContentProcessor:
    def __init__(
        self,
        event: ChatEvent,
        config: ContentProcessorConfig,
        language_model: LanguageModelInfo,
    ):
        self.config = config
        self.embedding_service = EmbeddingService(event=event)
        self.language_model = language_model
        self.encoder_name = language_model.encoder_name or DEFAULT_ENCODER_MODEL
        self.chunk_size = 1000  # Default chunk size
        self.chunking_max_workers = 10  # Default max workers

    async def run(self, query: str, pages: list[WebSearchResult]) -> list[WebPageChunk]:
        """
        Preprocess the pages content.
        Args:
            pages: list of pages.
        Returns:
            list[WebPageChunk]: List of processed webpage chunks.
        """

        pages = await self._process_pages(query, pages)

        pages_chunks = self._split_pages_to_chunks(pages)

        logger.info(f"Number of chunks total: {len(pages_chunks)}")

        return pages_chunks

    async def _process_pages(
        self, query: str, pages: list[WebSearchResult]
    ) -> list[WebSearchResult]:
        # Apply processing strategy with regex preprocessing as baseline
        logger.info(f"Processing pages with strategy: {self.config.strategy}")

        safe_task_executor = SafeTaskExecutor(logger=logger)

        results = await asyncio.gather(
            *[
                safe_task_executor.execute_async(
                    self._process_single_page,
                    page=page,
                    query=query,
                )
                for page in pages
            ]
        )

        processed_pages = []
        for result, page in zip(results, pages):
            if result.success:
                page = result.unpack()
            else:
                # Empty content to avoid overfilling the context in case processing strategy fails
                page.content = ""
            processed_pages.append(page)

        return processed_pages

    async def _process_single_page(
        self, page: WebSearchResult, query: str
    ) -> WebSearchResult:
        """Process a single page with optional regex preprocessing."""

        # Apply the enabled preprocessing steps
        page.content = self._preprocess_content(page.content)

        # Then apply strategy-specific processing
        match self.config.strategy:
            case ContentProcessingStartegy.SUMMARIZE:
                return await self._summarize_page(page, query)  # LLM processing
            case ContentProcessingStartegy.TRUNCATE:
                return await self._truncate_page(page)  # Token truncation
            case ContentProcessingStartegy.NONE:
                return page  # Raw content or regex cleaned

    async def _summarize_page(
        self, page: WebSearchResult, query: str
    ) -> WebSearchResult:
        """Summarize webpage content using LLM"""
        content = page.content
        # Check token count - hardcoded 2000 token minimum for summarization
        encoder = tiktoken.get_encoding(
            self.config.language_model.encoder_name or "cl100k_base"
        )
        token_count = len(encoder.encode(content))

        client = get_async_openai_client()
        logger.info(f"Summarizing webpage ({page.url}) with {token_count} tokens")

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.config.summarization_prompt},
            {"role": "user", "content": f"Query: {query}\nWebpage: {content}".strip()},
        ]
        response = await client.chat.completions.create(
            model=self.config.language_model.name,
            messages=messages,
            max_tokens=1000,
            temperature=0.1,
        )

        page.content = response.choices[0].message.content or ""
        return page

    async def _truncate_page(self, page: WebSearchResult) -> WebSearchResult:
        """Truncate page content to max tokens."""
        encoder = tiktoken.get_encoding(
            self.config.language_model.encoder_name or "cl100k_base"
        )
        tokens = encoder.encode(page.content)

        if len(tokens) > self.config.max_tokens:
            page.content = encoder.decode(tokens[: self.config.max_tokens])

        return page

    def _preprocess_content(self, content: str) -> str:
        """Smart preprocessing to remove navigation and UI clutter."""
        # Stage 1: Normalize encoding
        content = content.encode(encoding="utf-8", errors="ignore").decode()

        # Stage 2: Remove lines matching patterns
        lines = content.split("\n")
        filtered_lines = []

        for line in lines:
            should_keep = True
            for pattern in self.config.regex_line_removal_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_keep = False
                    break
            if should_keep:
                filtered_lines.append(line)

        content = "\n".join(filtered_lines)

        # Stage 3: Apply content transformations
        if self.config.remove_urls_from_markdown_links:
            for pattern, replacement in REGEX_CONTENT_TRANSFORMATIONS:
                content = re.sub(pattern, replacement, content)

        # Stage 4: Normalize whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"[ \t]{2,}", " ", content)

        return content.strip()

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

        chunk_size = self.chunk_size

        splitter = TokenTextSplitter(
            encoding_name=self.encoder_name,
            chunk_size=chunk_size,
            chunk_overlap=0,
        )

        chunks = splitter.split_text(page.content)

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
