from __future__ import annotations

from typing import Any, Self

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.components.internal_search.base import (
    SearchStringResult,
)
from unique_toolkit.components.internal_search.base.service import (
    InternalSearchBaseService,
)
from unique_toolkit.components.internal_search.knowledge_base.config import (
    KnowledgeBaseInternalSearchConfig,
)
from unique_toolkit.components.internal_search.knowledge_base.schemas import (
    KnowledgeBaseInternalSearchDeps,
    KnowledgeBaseInternalSearchState,
    _UnsetType,
)
from unique_toolkit.services import UniqueServiceFactory


class KnowledgeBaseInternalSearchService(
    InternalSearchBaseService[KnowledgeBaseInternalSearchDeps]
):
    _state: KnowledgeBaseInternalSearchState
    _dependencies: KnowledgeBaseInternalSearchDeps
    _config: KnowledgeBaseInternalSearchConfig  # pyright: ignore[reportIncompatibleVariableOverride]
    _config_model_cls = KnowledgeBaseInternalSearchConfig

    @classmethod
    def from_config(cls, config: KnowledgeBaseInternalSearchConfig) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        instance = cls()
        instance._config = config
        return instance

    def reset_state(self) -> None:
        self._state = KnowledgeBaseInternalSearchState(search_queries=[])

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> KnowledgeBaseInternalSearchDeps:
        factory = UniqueServiceFactory(settings=settings)
        return KnowledgeBaseInternalSearchDeps(
            chunk_relevancy_sorter=factory.chunk_relevancy_sorter(),
            knowledge_base_service=factory.knowledge_base_service(),
        )

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        # kb_service has some overloads that only accept some specific combinations of
        # scope_ids, metadata_filter, and content_ids
        # - if scope_ids, then nothing else
        # - if content_ids, then also metadata_filter is needed
        # - metadata_filter can be passed alone as well

        scope_ids = self._config.scope_ids
        metadata_filter = self._effective_metadata_filter
        content_ids = self._state.content_ids

        kwargs: dict[str, Any] = {
            "search_string": query,
            "search_type": self._config.search_type,
            "limit": self._config.limit,
            "reranker_config": self._config.reranker_config,
            "search_language": self._config.search_language,
            "score_threshold": self._config.score_threshold,
        }
        if scope_ids is not None:  # if defined, it takes precedence over other filters
            kwargs["scope_ids"] = scope_ids
        elif metadata_filter is not None:
            kwargs["metadata_filter"] = metadata_filter
            if content_ids is not None:
                kwargs["content_ids"] = content_ids
        else:
            raise RuntimeError(
                "KBSearchService requires either scope_ids or metadata_filter. "
                + "Set scope_ids or metadata_filter in config, or ensure the chat "
                + "context provides a filter."
            )

        chunks = (
            await self._dependencies.knowledge_base_service.search_content_chunks_async(
                **kwargs  # type: ignore[call-overload]
            )
        )
        return SearchStringResult(
            query=query,
            chunks=chunks,
        )

    @property
    def _effective_metadata_filter(self) -> dict[str, Any] | None:
        if not isinstance(self._state.metadata_filter_override, _UnsetType):
            return self._state.metadata_filter_override
        if self._context.chat is not None:
            return self._context.chat.metadata_filter
        return self._config.metadata_filter


__all__ = ["KnowledgeBaseInternalSearchService"]
