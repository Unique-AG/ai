from __future__ import annotations

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.components.internal_search.base import (
    SearchStringResult,
)
from unique_toolkit.components.internal_search.base.service import (
    InternalSearchExecutionBaseService,
)
from unique_toolkit.components.internal_search.chat.schemas import (
    ChatInternalSearchDeps,
)
from unique_toolkit.services import UniqueServiceFactory


class ChatInternalSearchService(
    InternalSearchExecutionBaseService[ChatInternalSearchDeps]
):
    _dependencies: ChatInternalSearchDeps

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> ChatInternalSearchDeps:
        if not context.chat:
            raise RuntimeError("ChatInternalSearchService requires a chat context")
        factory = UniqueServiceFactory(settings=settings)
        return ChatInternalSearchDeps(
            chunk_relevancy_sorter=factory.chunk_relevancy_sorter(),
            chat_service=factory.chat_service(),
        )

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        chunks = await self._dependencies.chat_service.search_content_chunks_async(
            search_string=query,
            search_type=self._config.search_type,
            limit=self._config.limit,
            reranker_config=self._config.reranker_config,
            search_language=self._config.search_language,
            score_threshold=self._config.score_threshold,
            content_ids=self._state.content_ids,
        )
        return SearchStringResult(
            query=query,
            chunks=chunks,
        )


__all__ = ["ChatInternalSearchService"]
