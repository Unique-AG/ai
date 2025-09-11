import asyncio
import logging
import re

import pandas as pd
import tiktoken
from langchain.text_splitter import TokenTextSplitter
from unidecode import unidecode
from unique_toolkit import LanguageModelService
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.embedding.service import EmbeddingService
from unique_toolkit.framework_utilities.openai import get_async_openai_client
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.tools.utils.execution.execution import SafeTaskExecutor

from unique_web_search.services.content_processing.config import (
    ContentProcessingConfig,
    ContentProcessingStartegy,
    WebPageChunk,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = logging.getLogger(__name__)


DEFAULT_ENCODER_MODEL = "cl100k_base"


class ContentAdapter:
    def __init__(
        self,
        event: ChatEvent,
        config: ContentProcessingConfig,
        llm_service: LanguageModelService,
        language_model: LanguageModelInfo,
    ):
        self.config = config
        self.embedding_service = EmbeddingService(event=event)
        self.language_model = language_model
        self.encoder_name = language_model.encoder_name or DEFAULT_ENCODER_MODEL
        self.llm_service = llm_service
        self.chunk_size = 1000  # Default chunk size
        self.chunking_max_workers = 10  # Default max workers

    async def run(self, query: str, pages: list[WebSearchResult]) -> pd.DataFrame:
        """
        Preprocess the pages content.

        Args:
            pages: list of pages.

        Returns:
            pd.DataFrame: DataFrame with the pages.
        """

        pages = await self._process_pages(query, pages)

        pages_chunks = self._split_pages_to_chunks(pages)

        logger.info(f"Number of chunks total: {len(pages_chunks)}")

        df_chunks = pd.DataFrame([record.model_dump() for record in pages_chunks])

        ###
        # If embedding reranking flag is false, return the chunks
        ###
        df_chunks = self._create_sources(df_chunks)
        return df_chunks

    async def _process_pages(
        self, query: str, pages: list[WebSearchResult]
    ) -> list[WebSearchResult]:
        # Step 1: Clean content if enabled
        if self.config.clean_enabled:
            logger.info(f"Cleaning {len(pages)} pages with LLM before processing")
            pages = await self._clean_pages(pages)

        # Step 2: Apply processing strategy - direct enum dispatch
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
        """Process a single page based on the configured strategy."""
        match self.config.strategy:
            case ContentProcessingStartegy.SUMMARIZE:
                return await self._summarize_page(page, query)
            case ContentProcessingStartegy.TRUNCATE:
                return await self._truncate_page(page)
            case ContentProcessingStartegy.NONE:
                return page

    async def _summarize_page(
        self, page: WebSearchResult, query: str
    ) -> WebSearchResult:
        """Summarize webpage content using LLM."""
        # Truncate first to avoid token limits - hardcoded 2000 token minimum
        truncated_page = await self._truncate_page(page)
        token_count = len(
            tiktoken.get_encoding(
                self.config.language_model.encoder_name or "cl100k_base"
            ).encode(truncated_page.content)
        )

        if token_count < 2000:  # Hardcoded minimum threshold
            return page

        logger.info(f"Summarizing webpage ({page.url}) with {token_count} tokens")

        client = get_async_openai_client()
        messages = [
            {"role": "system", "content": self.config.summarization_prompt},
            {
                "role": "user",
                "content": f"Query: {query}\nWebpage: {truncated_page.content}".strip(),
            },
        ]
        response = await client.chat.completions.create(
            model=self.config.language_model.name,
            messages=messages,
            max_tokens=1000,
            temperature=0.1,
        )

        page.content = response.choices[0].message.content
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

    async def _clean_pages(self, pages: list[WebSearchResult]) -> list[WebSearchResult]:
        """Clean pages using LLM-based content cleaning."""
        safe_task_executor = SafeTaskExecutor(logger=logger)

        results = await asyncio.gather(
            *[
                safe_task_executor.execute_async(
                    self._clean_single_page,
                    page=page,
                )
                for page in pages
            ]
        )

        cleaned_pages = []
        for result, page in zip(results, pages):
            if result.success:
                page = result.unpack()
            else:
                logger.warning(
                    f"Cleaning failed for {page.url}, keeping original content"
                )
            cleaned_pages.append(page)

        return cleaned_pages

    async def _clean_single_page(self, page: WebSearchResult) -> WebSearchResult:
        """Clean a single webpage using LLM."""
        # Apply preprocessing
        preprocessed_content = self._preprocess_content(page.content)
        truncated_content = self._smart_truncate(preprocessed_content)

        logger.info(
            f"Cleaning webpage ({page.url}) with {len(truncated_content)} characters"
        )

        messages = (
            MessagesBuilder()
            .system_message_append(self.config.cleaning_prompt)
            .user_message_append(
                f"Clean and condense this website content into focused markdown:\n\n{truncated_content}"
            )
            .build()
        )

        response = await self.llm_service.complete_async(
            messages=messages,
            model_name=self.config.language_model.name,
            max_tokens=1000,  # Hardcoded cleaning max tokens
            temperature=0.1,
        )

        page.content = response.choices[0].message.content  # type: ignore
        return page

    def _preprocess_content(self, content: str) -> str:
        """Smart preprocessing to remove navigation and UI clutter."""
        # Remove URLs but keep context
        content = re.sub(r"https?://[^\s\])]+", "[URL]", content)

        # Remove navigation and UI patterns
        nav_patterns = [
            r"^[\*\+\-]\s+(Home|Menu|Navigate|Skip to|Sign In|Subscribe).*$",
            r"^[\?\[]?(Subscribe|Sign [Iu]p|Follow|Share|Like)[\]?]?.*$",
            r"Cookie.*|Privacy Policy|Terms of Service",
            r"^\s*\[.*accessibility.*\].*$",
        ]

        lines = content.split("\n")
        filtered_lines = []

        for line in lines:
            should_keep = True
            for pattern in nav_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_keep = False
                    break
            if should_keep:
                filtered_lines.append(line)

        content = "\n".join(filtered_lines)

        # Normalize whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"[ \t]{2,}", " ", content)

        return content.strip()

    def _smart_truncate(self, content: str, max_chars: int = 12000) -> str:
        """Intelligent truncation preserving structure."""
        if len(content) <= max_chars:
            return content

        # Try to keep structure: beginning + middle sample + end
        paragraphs = content.split("\n\n")
        if len(paragraphs) <= 3:
            return content[:max_chars]

        # Keep first 2 and last 1 paragraphs, sample middle
        keep_ratio = max_chars / len(content)
        middle_keep = max(1, int(len(paragraphs[2:-1]) * keep_ratio))

        result_parts = paragraphs[:2]
        if middle_keep > 0:
            result_parts.extend(paragraphs[2 : 2 + middle_keep])
        result_parts.extend(paragraphs[-1:])

        result = "\n\n".join(result_parts)

        # Final truncation if still too long
        if len(result) > max_chars:
            result = result[:max_chars] + "\n\n[Content truncated...]"

        return result

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

    def _create_sources(self, df_chunks: pd.DataFrame):
        """
        Create source info for referencing in stream.

        Args:
            df_chunks: The DataFrame with the chunks.
        """

        if df_chunks.empty:
            return df_chunks

        # Function to create the source dictionary
        def create_source(row):
            display_link = row["display_link"]

            # Convert to ascii
            title = unidecode(row["title"])

            name = f'{display_link}: "{title}"'

            content_chunk = ContentChunk(
                id=name,
                text=row["content"],
                order=row["order"],
                start_page=None,
                end_page=None,
                key=name,
                chunk_id=row["order"],
                url=row["url"],
                title=name,
            )

            return content_chunk.model_dump()

        df_chunks["source"] = df_chunks.apply(create_source, axis=1)

        return df_chunks

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
                    content=self._wrap_with_snipper(page.snippet, page.content),
                    order="0",
                )
            ]

        records = [
            WebPageChunk(
                url=page.url,
                display_link=page.display_link,
                title=page.title,
                snippet=page.snippet,
                content=self._wrap_with_snipper(page.snippet, chunk),
                order=str(order),
            )
            for order, chunk in enumerate(chunks)
        ]
        return records

    @staticmethod
    def _wrap_with_snipper(snippet: str, content: str) -> str:
        if len(content) > 0:
            return f"<SearchEngineSnippet>{snippet}</SearchEngineSnippet>\n\n<FetchContent>{content}</FetchContent>"
        return f"<SearchEngineSnippet>{snippet}</SearchEngineSnippet>"
