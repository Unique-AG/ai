from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self, cast

from unique_toolkit._common.metadata_filter_scope import (
    build_folder_id_in_clause,
    merge_scope_clause_into_metadata_filter,
)
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
    _resolved_metadata_filter: dict[str, Any] | None | _UnsetType

    @classmethod
    def from_config(cls, config: KnowledgeBaseInternalSearchConfig) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        instance = cls()
        instance._config = config
        return instance

    def reset_state(self) -> None:
        self._state = KnowledgeBaseInternalSearchState(search_queries=[])
        self._resolved_metadata_filter = UNSET

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> KnowledgeBaseInternalSearchDeps:
        factory = UniqueServiceFactory(settings=settings)
        return KnowledgeBaseInternalSearchDeps(
            knowledge_base_service=factory.knowledge_base_service(),
        )

    def _extra_debug_info(self) -> dict[str, Any]:
        resolved = self._resolved_metadata_filter
        effective = (
            resolved
            if not isinstance(resolved, _UnsetType)
            else self._effective_metadata_filter
        )
        debug_info: dict[str, Any] = {"metadataFilter": effective}
        if self._effective_scope_ids is not None:
            debug_info["scopeIds"] = self._effective_scope_ids
        return debug_info

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        metadata_filter = self._effective_metadata_filter
        scope_ids = self._effective_scope_ids

        if scope_ids is not None:
            clause = build_folder_id_in_clause(scope_ids)
            metadata_filter = merge_scope_clause_into_metadata_filter(
                clause, metadata_filter
            )
            self._resolved_metadata_filter = metadata_filter

        if metadata_filter is None:
            raise RuntimeError(
                "KnowledgeBaseInternalSearchService requires a metadata filter "
                "(config.metadata_filter, deprecated config.scope_ids, chat context "
                "metadata_filter, or state override). content_ids alone is not "
                "supported without a metadata filter."
            )

        kb = self._dependencies.knowledge_base_service
        content_ids = self._state.content_ids
        kwargs: dict[str, Any] = dict(
            search_string=query,
            search_type=self._config.search.search_type,
            limit=self._config.filtering.limit,
            search_language=self._config.search.search_language,
            score_threshold=self._config.filtering.score_threshold,
            reranker_config=self._config.reranker_config,
            metadata_filter=metadata_filter,
        )
        if content_ids is not None:
            kwargs["content_ids"] = content_ids
        chunks = await kb.search_content_chunks_async(**kwargs)
        return SearchStringResult(query=query, chunks=chunks)

    @property
    def _effective_metadata_filter(self) -> Mapping[str, Any] | None:
        if self._state.metadata_filter_override is not UNSET:
            return cast("dict[str, Any] | None", self._state.metadata_filter_override)
        if self._context.chat is not None:
            return self._context.chat.metadata_filter
        return self._config.metadata_filter

    @property
    def _effective_scope_ids(self) -> list[str] | None:
        if self._state.metadata_filter_override is not UNSET:
            return None
        if self._context.chat is not None:
            return None
        return self._config.scope_ids


__all__ = ["KnowledgeBaseInternalSearchService"]
