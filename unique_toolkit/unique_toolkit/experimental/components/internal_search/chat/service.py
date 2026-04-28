from __future__ import annotations

from typing import Self

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.experimental.components.internal_search.base import (
    SearchStringResult,
)
from unique_toolkit.experimental.components.internal_search.base.service import (
    InternalSearchBaseService,
)
from unique_toolkit.experimental.components.internal_search.chat.config import (
    ChatInternalSearchConfig,
)
from unique_toolkit.experimental.components.internal_search.chat.schemas import (
    ChatInternalSearchDeps,
)
from unique_toolkit.services import UniqueServiceFactory


class ChatInternalSearchService(InternalSearchBaseService[ChatInternalSearchDeps]):
    _dependencies: ChatInternalSearchDeps
    _config: ChatInternalSearchConfig  # pyright: ignore[reportIncompatibleVariableOverride]
    _config_model_cls = ChatInternalSearchConfig

    @classmethod
    def from_config(cls, config: ChatInternalSearchConfig) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        instance = cls()
        instance._config = config
        return instance

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> ChatInternalSearchDeps:
        if not context.chat:
            raise RuntimeError("ChatInternalSearchService requires a chat context")
        factory = UniqueServiceFactory(settings=settings)
        return ChatInternalSearchDeps(
            chat_service=factory.chat_service(),
        )

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        chunks = await self._dependencies.chat_service.search_content_chunks_async(
            search_string=query,
            search_type=self._config.search_type,
            limit=self._config.limit,
            search_language=self._config.search_language,
            score_threshold=self._config.score_threshold,
            reranker_config=self._config.reranker_config,
            content_ids=self._state.content_ids,
        )
        return SearchStringResult(
            query=query,
            chunks=chunks,
        )


__all__ = ["ChatInternalSearchService"]
