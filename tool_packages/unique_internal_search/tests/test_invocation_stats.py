from typing import Any
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from unique_toolkit._common.chunk_relevancy_sorter.schemas import (
    ChunkRelevancy,
    ChunkRelevancySorterResult,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.service import (
    InternalSearchService,
    InternalSearchTool,
    _append_chunk_relevancy_invocation_stats,
)


def _usage(total: int = 3) -> LanguageModelTokenUsage:
    return LanguageModelTokenUsage(
        completion_tokens=1,
        prompt_tokens=total - 1,
        total_tokens=total,
    )


def _relevancy_result(
    *,
    model_name: str = DEFAULT_GPT_4o,
    total_tokens: int = 3,
) -> EvaluationMetricResult:
    return EvaluationMetricResult(
        value="high",
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        reason="Test reason",
        invocation_stats=[
            LanguageModelInvocationStats.from_usage(
                model_name,
                _usage(total_tokens),
                source="context_relevancy",
            )
        ],
    )


class TestAppendChunkRelevancyInvocationStats:
    def test_remaps_primary_and_fallback_sources(
        self,
        base_internal_search_config: InternalSearchConfig,
        sample_content_chunks: list[ContentChunk],
    ) -> None:
        config = base_internal_search_config.chunk_relevancy_sort_config.model_copy(
            deep=True
        )
        config.language_model = LanguageModelInfo.from_name(DEFAULT_GPT_4o)
        config.fallback_language_model = LanguageModelInfo.from_name("gpt-4o-mini")
        primary = config.language_model.name
        fallback = config.fallback_language_model.name
        sorter_result = ChunkRelevancySorterResult(
            relevancies=[
                ChunkRelevancy(
                    chunk=sample_content_chunks[0],
                    relevancy=_relevancy_result(model_name=primary, total_tokens=5),
                ),
                ChunkRelevancy(
                    chunk=sample_content_chunks[1],
                    relevancy=_relevancy_result(model_name=fallback, total_tokens=7),
                ),
            ]
        )
        accumulator: list[LanguageModelInvocationStats] = []

        _append_chunk_relevancy_invocation_stats(sorter_result, config, accumulator)

        assert len(accumulator) == 2
        assert accumulator[0].source == "internal_search_chunk_relevancy"
        assert accumulator[0].model_name == primary
        assert accumulator[0].token_usage.total_tokens == 5
        assert accumulator[1].source == "internal_search_chunk_relevancy_fallback"
        assert accumulator[1].model_name == fallback
        assert accumulator[1].token_usage.total_tokens == 7

    def test_identical_model_names__uses_primary_source(
        self,
        base_internal_search_config: InternalSearchConfig,
        sample_content_chunks: list[ContentChunk],
    ) -> None:
        config = base_internal_search_config.chunk_relevancy_sort_config
        model_name = config.language_model.name
        sorter_result = ChunkRelevancySorterResult(
            relevancies=[
                ChunkRelevancy(
                    chunk=sample_content_chunks[0],
                    relevancy=_relevancy_result(model_name=model_name),
                )
            ]
        )
        accumulator: list[LanguageModelInvocationStats] = []

        _append_chunk_relevancy_invocation_stats(sorter_result, config, accumulator)

        assert len(accumulator) == 1
        assert accumulator[0].source == "internal_search_chunk_relevancy"


class TestInternalSearchInvocationStats:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__relevancy_enabled__records_stats_on_accumulator(
        self,
        base_internal_search_config: InternalSearchConfig,
        mock_content_service: ContentService,
        mock_chunk_relevancy_sorter: Any,
        mock_logger: Any,
        sample_content_chunks: list[ContentChunk],
    ) -> None:
        base_internal_search_config.chunk_relevancy_sort_config.enabled = True
        config = base_internal_search_config.chunk_relevancy_sort_config
        service = InternalSearchService(
            config=base_internal_search_config,
            content_service=mock_content_service,
            chunk_relevancy_sorter=mock_chunk_relevancy_sorter,
            chat_id="chat_123",
            logger=mock_logger,
        )
        mock_content_service.search_contents_async = AsyncMock(return_value=[])
        mock_content_service.search_content_chunks_async = AsyncMock(
            return_value=sample_content_chunks
        )
        mock_chunk_relevancy_sorter.run = AsyncMock(
            return_value=ChunkRelevancySorterResult(
                relevancies=[
                    ChunkRelevancy(
                        chunk=chunk,
                        relevancy=_relevancy_result(
                            model_name=config.language_model.name
                        ),
                    )
                    for chunk in sample_content_chunks
                ]
            )
        )

        invocation_stats: list[LanguageModelInvocationStats] = []
        await service.search("test query", invocation_stats=invocation_stats)

        mock_chunk_relevancy_sorter.run.assert_called_once()
        assert len(invocation_stats) == len(sample_content_chunks)
        assert all(
            stat.source == "internal_search_chunk_relevancy"
            for stat in invocation_stats
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__relevancy_disabled__leaves_accumulator_empty(
        self,
        base_internal_search_config: InternalSearchConfig,
        mock_content_service: ContentService,
        mock_chunk_relevancy_sorter: Any,
        mock_logger: Any,
        sample_content_chunks: list[ContentChunk],
    ) -> None:
        base_internal_search_config.chunk_relevancy_sort_config.enabled = False
        service = InternalSearchService(
            config=base_internal_search_config,
            content_service=mock_content_service,
            chunk_relevancy_sorter=mock_chunk_relevancy_sorter,
            chat_id="chat_123",
            logger=mock_logger,
        )
        mock_content_service.search_contents_async = AsyncMock(return_value=[])
        mock_content_service.search_content_chunks_async = AsyncMock(
            return_value=sample_content_chunks
        )

        invocation_stats: list[LanguageModelInvocationStats] = []
        await service.search("test query", invocation_stats=invocation_stats)

        assert invocation_stats == []
        mock_chunk_relevancy_sorter.run.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_invocation_stats_on_tool_response(
        self,
        base_internal_search_config: InternalSearchConfig,
        mock_chat_event: Any,
        mock_language_model_function: Any,
        sample_content_chunks: list[ContentChunk],
    ) -> None:
        base_internal_search_config.chunk_relevancy_sort_config.enabled = True
        recorded = [
            LanguageModelInvocationStats.from_usage(
                DEFAULT_GPT_4o,
                _usage(4),
                source="internal_search_chunk_relevancy",
            )
        ]

        async def _search_side_effect(*args: Any, **kwargs: Any) -> list[ContentChunk]:
            stats = kwargs.get("invocation_stats")
            if stats is not None:
                stats.extend(recorded)
            return sample_content_chunks

        with (
            patch(
                "unique_internal_search.service.ContentService.from_event"
            ) as mock_content_service_cls,
            patch(
                "unique_internal_search.service.ChunkRelevancySorter.from_event"
            ) as mock_sorter_cls,
            patch.object(
                InternalSearchTool,
                "search",
                new_callable=AsyncMock,
                side_effect=_search_side_effect,
            ),
            patch(
                "unique_internal_search.service.feature_flags.enable_new_answers_ui_un_14411.is_enabled",
                return_value=False,
            ),
            patch(
                "unique_internal_search.service.Tool.tool_progress_reporter",
                new_callable=PropertyMock,
                return_value=None,
            ),
        ):
            mock_content_service_cls.return_value = Mock()
            mock_sorter_cls.return_value = Mock()
            tool = InternalSearchTool(base_internal_search_config, mock_chat_event)
            tool._message_step_logger = None

            response = await tool.run(mock_language_model_function)

        assert isinstance(response, ToolCallResponse)
        assert response.invocation_stats == recorded
