import asyncio
import logging

import pandas as pd
from langchain.text_splitter import TokenTextSplitter
from pydantic import BaseModel, Field
from unidecode import unidecode
from unique_toolkit import LanguageModelService
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.embedding.service import EmbeddingService
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.tools.config import get_configuration_dict
from unique_toolkit.tools.utils.execution.execution import SafeTaskExecutor

from unique_web_search.services.preprocessing.content_processing import (
    ProcessingStrategyType,
    get_strategy,
)
from unique_web_search.services.preprocessing.content_processing.strategies import (
    TruncatePageToMaxTokensConfig,
)
from unique_web_search.services.preprocessing.schema import (
    WebPageChunk,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = logging.getLogger(__name__)


DEFAULT_ENCODER_MODEL = "cl100k_base"


class ContentAdapterConfig(BaseModel):
    model_config = get_configuration_dict()
    chunk_size: int = Field(
        default=1000,
        description="Number of chunks to split the search results",
    )

    chunking_max_workers: int = Field(
        default=10,
        description="Number of workers to embed search results",
    )

    content_processing_strategy_config: ProcessingStrategyType = Field(
        default_factory=TruncatePageToMaxTokensConfig,
        description="The strategy to use for content processing",
        discriminator="strategy",
    )


class ContentAdapter:
    def __init__(
        self,
        event: ChatEvent,
        config: ContentAdapterConfig,
        llm_service: LanguageModelService,
        language_model: LanguageModelInfo,
    ):
        self.config = config
        self.embedding_service = EmbeddingService(event=event)
        self.language_model = language_model
        self.encoder_name = language_model.encoder_name or DEFAULT_ENCODER_MODEL
        self.llm_service = llm_service

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

    # TODO: Find a tracking solution
    # @track(
    #     tags=["content_processing"],
    # )
    async def _process_pages(
        self, query: str, pages: list[WebSearchResult]
    ) -> list[WebSearchResult]:
        logger.info(
            f"Processing pages with strategy: {self.config.content_processing_strategy_config.strategy}"
        )
        content_processing_strategy = get_strategy(
            strategy=self.config.content_processing_strategy_config,
            query=query,
            language_model=self.language_model,
            llm_service=self.llm_service,
        )

        safe_task_executor = SafeTaskExecutor(
            logger=logger,
        )

        results = await asyncio.gather(
            *[
                safe_task_executor.execute_async(
                    content_processing_strategy,
                    page=page,
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

        chunk_size = self.config.chunk_size

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
