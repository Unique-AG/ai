from __future__ import annotations

import logging
from typing import Any, Self, cast

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.experimental.components.internal_search.base import (
    SearchStringResult,
)
from unique_toolkit.experimental.components.internal_search.base.service import (
    InternalSearchBaseService,
)
from unique_toolkit.experimental.components.internal_search.knowledge_base.config import (
    KnowledgeBaseInternalSearchConfig,
)
from unique_toolkit.experimental.components.internal_search.knowledge_base.schemas import (
    UNSET,
    KnowledgeBaseInternalSearchDeps,
    KnowledgeBaseInternalSearchState,
)
from unique_toolkit.services import UniqueServiceFactory

_logger = logging.getLogger(__name__)


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
            knowledge_base_service=factory.knowledge_base_service(),
        )

    def _extra_debug_info(self) -> dict[str, Any]:
        return {"metadataFilter": self._effective_metadata_filter}

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        # The KB search API accepts mutually exclusive filter combinations:
        # - scope_ids alone (no metadata_filter or content_ids)
        # - metadata_filter alone, or metadata_filter + content_ids
        kb = self._dependencies.knowledge_base_service
        base = {
            "search_string": query,
            "search_type": self._config.search_type,
            "limit": self._config.limit,
            "search_language": self._config.search_language,
            "score_threshold": self._config.score_threshold,
            "reranker_config": self._config.reranker_config,
        }

        scope_ids = self._config.scope_ids
        metadata_filter = self._effective_metadata_filter
        content_ids = self._state.content_ids

        if scope_ids is not None:
            _logger.debug("scope_ids set; ignoring metadata_filter for this query.")
            chunks = await kb.search_content_chunks_async(**base, scope_ids=scope_ids)
        elif metadata_filter is not None:
            if content_ids is not None:
                chunks = await kb.search_content_chunks_async(
                    **base, metadata_filter=metadata_filter, content_ids=content_ids
                )
            else:
                chunks = await kb.search_content_chunks_async(
                    **base, metadata_filter=metadata_filter
                )
        else:
            raise RuntimeError(
                "KBSearchService requires either scope_ids or metadata_filter. "
                "Set scope_ids or metadata_filter in config, or ensure the chat "
                "context provides a filter."
            )

        return SearchStringResult(query=query, chunks=chunks)

    @property
    def _effective_metadata_filter(self) -> dict[str, Any] | None:
        if self._state.metadata_filter_override is not UNSET:
            return cast("dict[str, Any] | None", self._state.metadata_filter_override)
        if self._context.chat is not None:
            return self._context.chat.metadata_filter
        return self._config.metadata_filter


__all__ = ["KnowledgeBaseInternalSearchService"]
