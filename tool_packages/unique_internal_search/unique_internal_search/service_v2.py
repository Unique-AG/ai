from __future__ import annotations

import asyncio
from collections.abc import Sequence

from typing_extensions import Self
from unique_toolkit._common.chunk_relevancy_sorter.exception import (
    ChunkRelevancySorterException,
)
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.utils import (
    merge_content_chunks,
    pick_content_chunks_for_token_window,
    sort_content_chunks,
)
from unique_toolkit.services.chat_service import ChatService
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

from unique_internal_search.base_service import BaseService
from unique_internal_search.schemas import (
    UNSET,
    InternalSearchDeps,
    InternalSearchProgressMessage,
    InternalSearchResult,
    InternalSearchServiceConfig,
    InternalSearchState,
    SearchStage,
)
from unique_internal_search.utils import (
    SearchStringResult,
    clean_search_string,
    interleave_search_results_round_robin,
)


class InternalSearchService(
    BaseService[
        InternalSearchResult,
        InternalSearchServiceConfig,
        InternalSearchState,
        InternalSearchProgressMessage,
        InternalSearchDeps,
    ]
):
    _config_model_cls = InternalSearchServiceConfig

    @classmethod
    def from_config(cls, config: InternalSearchServiceConfig) -> Self:
        instance = cls()
        instance._config = config
        return instance

    def bind_settings(self, settings: UniqueSettings) -> Self:
        context = UniqueContext.from_settings(settings)
        self._context = context
        self._dependencies = InternalSearchDeps(
            chunk_relevancy_sorter=ChunkRelevancySorter.from_settings(settings),
            kb_service=KnowledgeBaseService.from_context(context),
            chat_service=ChatService.from_context(context) if context.chat else None,
        )
        return self

    def reset_state(self) -> None:
        self._state = InternalSearchState(
            search_queries=[],
            chat_only=self._config.chat_only,
        )

    @property
    def _effective_metadata_filter(self) -> dict | None:
        if self._state.metadata_filter_override is not UNSET:
            return self._state.metadata_filter_override  # type: ignore[return-value]
        if self._context.chat:
            return self._context.chat.metadata_filter
        return None

    @property
    def _effective_chat_id(self) -> str | None:
        """Resolve the chat_id to use for file scoping.

        parent_chat_id takes precedence — when this service runs as a subagent,
        uploaded files belong to the parent chat, not the current (sub)chat.
        Returns None when chatless or when exclude_uploaded_files is set.
        """
        if self._config.exclude_uploaded_files or not self._context.chat:
            return None
        return self._context.chat.parent_chat_id or self._context.chat.chat_id

    async def run(self) -> InternalSearchResult:
        search_queries = self._normalise_queries(self._state.search_queries)
        chat_only, metadata_filter = await self._resolve_search_scope()

        await self.post_progress_message(
            InternalSearchProgressMessage(
                stage=SearchStage.RETRIEVING,
                status=MessageLogStatus.RUNNING,
                search_queries=search_queries,
            )
        )

        results = await asyncio.gather(
            *[
                self._search_single_query(
                    query=query,
                    metadata_filter=metadata_filter,
                    chat_only=chat_only,
                    content_ids=self._state.content_ids,
                )
                for query in search_queries
            ],
            return_exceptions=True,
        )

        found = self._collect_results(results, search_queries)

        if self._config.chunk_relevancy_sort_config.enabled:
            await self.post_progress_message(
                InternalSearchProgressMessage(
                    stage=SearchStage.RESORTING,
                    status=MessageLogStatus.RUNNING,
                    search_queries=search_queries,
                )
            )
            for result in found:
                result.chunks = await self._resort_chunks(result.chunks, result.query)

        await self.post_progress_message(
            InternalSearchProgressMessage(
                stage=SearchStage.POSTPROCESSING,
                status=MessageLogStatus.RUNNING,
                search_queries=search_queries,
            )
        )

        if self._config.enable_multiple_search_strings_execution and len(found) > 1:
            found = interleave_search_results_round_robin(found)

        all_chunks = [chunk for result in found for chunk in result.chunks]
        selected = pick_content_chunks_for_token_window(
            all_chunks,
            self._state.get_max_tokens(
                percentage=self._config.percentage_of_input_tokens_for_sources,
                fallback=self._config.max_tokens_for_sources,
            ),
            model_info=self._state.language_model_info,
        )

        if self._config.chunked_sources:
            selected = sort_content_chunks(selected)
        else:
            selected = merge_content_chunks(selected)

        await self.post_progress_message(
            InternalSearchProgressMessage(
                stage=SearchStage.COMPLETED,
                status=MessageLogStatus.COMPLETED,
                search_queries=search_queries,
                chunks=selected,
            )
        )

        return InternalSearchResult(
            chunks=selected,
            debug_info={
                "searchStrings": search_queries,
                "metadataFilter": metadata_filter,
                "chatOnly": chat_only,
            },
        )

        # TODO : discuss if we want to make self.reset_state() automatically or not.

    async def _resolve_search_scope(self) -> tuple[bool, dict | None]:
        """Derive effective (chat_only, metadata_filter) for this invocation.

        scope_to_chat_on_upload can upgrade chat_only to True if files exist in
        the current chat. When chat_only=True, metadata_filter is always None —
        chat-file scoping is incompatible with a metadata filter.

        Does not mutate state or context.
        """
        chat_only = self._state.chat_only

        if not chat_only and self._config.scope_to_chat_on_upload:
            if await self._has_uploaded_files():
                chat_only = True

        metadata_filter = None if chat_only else self._effective_metadata_filter
        return chat_only, metadata_filter

    async def _has_uploaded_files(self) -> bool:
        """Return True if any files are owned by the current chat session."""
        chat_service = self._dependencies.chat_service
        if chat_service is None:
            return False
        chat_id = self._effective_chat_id
        if not chat_id:
            return False
        files = await chat_service.search_contents_async(
            where={"ownerId": {"equals": chat_id}},
        )
        return bool(files)

    def _normalise_queries(self, queries: list[str]) -> list[str]:
        cleaned = [clean_search_string(q) for q in queries]
        deduped = list(dict.fromkeys(cleaned))
        return deduped[: self._config.max_search_strings]

    async def _search_single_query(
        self,
        *,
        query: str,
        metadata_filter: dict | None,
        chat_only: bool,
        content_ids: list[str] | None,
    ) -> SearchStringResult:
        deps = self._dependencies
        try:
            if chat_only:
                if deps.chat_service is None:
                    raise RuntimeError("chat_service is required for chat_only search")
                chunks = await deps.chat_service.search_content_chunks_async(
                    search_string=query,
                    search_type=self._config.search_type,
                    limit=self._config.limit,
                    reranker_config=self._config.reranker_config,
                    search_language=self._config.search_language,
                    scope_ids=self._config.scope_ids,
                    metadata_filter=metadata_filter,
                    content_ids=content_ids,
                    score_threshold=self._config.score_threshold,
                )
            else:
                chunks = await deps.kb_service.search_content_chunks_async(
                    search_string=query,
                    search_type=self._config.search_type,
                    limit=self._config.limit,
                    reranker_config=self._config.reranker_config,
                    search_language=self._config.search_language,
                    scope_ids=self._config.scope_ids,
                    metadata_filter=metadata_filter,
                    content_ids=content_ids,
                    score_threshold=self._config.score_threshold,
                )
        except Exception as e:
            self.logger.error("Error in search_content_chunks_async call: %s", e)
            raise
        return SearchStringResult(query=query, chunks=chunks)

    def _collect_results(
        self,
        results: Sequence[SearchStringResult | BaseException],
        queries: list[str],
    ) -> list[SearchStringResult]:
        successful: list[SearchStringResult] = []
        for i, result in enumerate(results, start=1):
            if isinstance(result, BaseException):
                self.logger.error("Search failed for query #%d/%d", i, len(queries))
            else:
                self.logger.info(
                    "Found %d chunks (query %d/%d)", len(result.chunks), i, len(queries)
                )
                successful.append(result)
        return successful

    async def _resort_chunks(
        self, chunks: list[ContentChunk], query: str
    ) -> list[ContentChunk]:
        self.logger.info("Resorting %d search results...", len(chunks))
        try:
            result = await self._dependencies.chunk_relevancy_sorter.run(
                input_text=query,
                chunks=chunks,
                config=self._config.chunk_relevancy_sort_config,
            )
            return result.content_chunks
        except ChunkRelevancySorterException as e:
            self.logger.warning("Chunk resorting failed: %s", e.error_message)
            return chunks
