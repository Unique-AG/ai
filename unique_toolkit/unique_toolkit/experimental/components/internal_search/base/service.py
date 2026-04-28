import asyncio
from abc import abstractmethod
from collections.abc import Sequence
from typing import Any, Self

from typing_extensions import Generic

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content import ContentChunk
from unique_toolkit.experimental.components._base import BaseService
from unique_toolkit.experimental.components.internal_search.base.config import (
    InternalSearchConfig,
)
from unique_toolkit.experimental.components.internal_search.base.schemas import (
    InternalSearchProgressMessage,
    InternalSearchResult,
    InternalSearchStage,
    InternalSearchState,
    SearchStringResult,
    TInternalSearchDeps,
)
from unique_toolkit.experimental.components.internal_search.base.utils import (
    clean_search_string,
    interleave_search_results_round_robin,
)


class InternalSearchBaseService(  # pyright: ignore[reportImplicitAbstractClass]
    BaseService[
        InternalSearchResult,
        InternalSearchConfig,
        InternalSearchState,
        InternalSearchProgressMessage,
        TInternalSearchDeps,  # still variable, defined based on chat or kb
    ],
    Generic[TInternalSearchDeps],
):
    _config_model_cls = InternalSearchConfig

    # Define needed methods from BaseService
    @classmethod
    def from_config(cls, config: InternalSearchConfig) -> Self:
        instance = cls()
        instance._config = config
        return instance

    def bind_settings(self, settings: UniqueSettings) -> Self:
        context: UniqueContext = settings.context
        self._context = context
        self._dependencies = self._make_dependencies(settings, context)
        self.reset_state()
        return self

    def reset_state(self) -> None:
        self._state = InternalSearchState(search_queries=[])

    async def run(self) -> InternalSearchResult:
        self._validate_state()
        search_queries = self._normalise_queries(self._state.search_queries)

        await self.post_progress_message(
            InternalSearchProgressMessage(
                stage=InternalSearchStage.RETRIEVING,
                status=MessageLogStatus.RUNNING,
                search_queries=search_queries,
            )
        )

        results = await asyncio.gather(
            *[self._search_single_query(query=q) for q in search_queries],
            return_exceptions=True,
        )

        found = self._collect_results(results, search_queries)
        return await self._finalize_run(
            search_queries,
            found,
            debug_info={
                "searchStrings": search_queries
            },  # camelCase: wire-protocol key consumed by downstream logging/analytics
        )

    # Abstract methods - need to define them in Subclasses
    @abstractmethod
    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> TInternalSearchDeps: ...

    @abstractmethod
    async def _search_single_query(self, *, query: str) -> SearchStringResult: ...

    # Utilities - used in other methods or subclasses methods

    def _validate_state(self):
        if not self._state.search_queries:
            raise ValueError("State must have at least one search query before run().")

    def _normalise_queries(self, queries: list[str]) -> list[str]:
        cleaned = [clean_search_string(q) for q in queries]
        deduped = list(dict.fromkeys(cleaned))
        return deduped[: self._config.max_search_strings]

    def _collect_results(
        self, results: Sequence[SearchStringResult | BaseException], queries: list[str]
    ):
        successful: list[SearchStringResult] = []
        for i, result in enumerate(results, start=1):
            if isinstance(result, BaseException):
                self.logger.error(
                    "Search failed for query #%d/%d", i, len(queries), exc_info=result
                )
            else:
                self.logger.info(
                    "Found %d chunks (query %d/%d)",
                    len(result.chunks),
                    i,
                    len(queries),
                )
                successful.append(result)
        return successful

    async def _finalize_run(
        self,
        search_queries: list[str],
        found: list[SearchStringResult],
        debug_info: dict[str, Any],
    ) -> InternalSearchResult:
        await self.post_progress_message(
            InternalSearchProgressMessage(
                stage=InternalSearchStage.POSTPROCESSING,
                status=MessageLogStatus.RUNNING,
                search_queries=search_queries,
            )
        )

        if self._config.enable_multiple_search_strings_execution and len(found) > 1:
            found = interleave_search_results_round_robin(found)

        chunks: list[ContentChunk] = [
            chunk for result in found for chunk in result.chunks
        ]

        await self.post_progress_message(
            InternalSearchProgressMessage(
                stage=InternalSearchStage.COMPLETED,
                status=MessageLogStatus.COMPLETED,
                search_queries=search_queries,
                chunks=chunks,
            )
        )

        return InternalSearchResult(
            chunks=chunks,
            debug_info=debug_info,
        )


__all__ = ["InternalSearchBaseService"]
