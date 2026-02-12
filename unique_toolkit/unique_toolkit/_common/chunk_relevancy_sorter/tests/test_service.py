from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.exception import (
    ChunkRelevancySorterException,
)
from unique_toolkit._common.chunk_relevancy_sorter.schemas import (
    ChunkRelevancy,
    ChunkRelevancySorterResult,
)
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.agentic.evaluation.context_relevancy.schema import (
    StructuredOutputConfig,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit.language_model.infos import LanguageModelInfo


@pytest.fixture
def event():
    event = MagicMock(spec=ChatEvent)
    event.payload = MagicMock()
    event.payload.user_message = MagicMock()
    event.payload.user_message.text = "Test query"
    event.user_id = "user_0"
    event.company_id = "company_0"
    return event


@pytest.fixture
def mock_chunks():
    return [
        ContentChunk(
            id=f"chunk_{i}",
            order=i,
            chunk_id=f"chunk_{i}",
            text=f"Test content {i}",
        )
        for i in range(3)
    ]


@pytest.fixture
def config():
    return ChunkRelevancySortConfig(
        enabled=True,
        relevancy_levels_to_consider=["high", "medium", "low"],
        relevancy_level_order={"high": 0, "medium": 1, "low": 2},
        language_model=LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL),
        fallback_language_model=LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL),
        structured_output_config=StructuredOutputConfig(
            enabled=False,
            extract_fact_list=False,
        ),
    )


@pytest.fixture
def chunk_relevancy_sorter(event):
    return ChunkRelevancySorter(event)


@pytest.mark.asyncio
async def test_run_disabled_config(chunk_relevancy_sorter, mock_chunks, config):
    config.enabled = False
    result = await chunk_relevancy_sorter.run("test input", mock_chunks, config)

    assert isinstance(result, ChunkRelevancySorterResult)
    assert result.content_chunks == mock_chunks
    assert len(result.content_chunks) == len(mock_chunks)


@pytest.mark.asyncio
async def test_run_enabled_config(chunk_relevancy_sorter, mock_chunks, config):
    with patch.object(chunk_relevancy_sorter, "_run_chunk_relevancy_sort") as mock_sort:
        mock_sort.return_value = ChunkRelevancySorterResult.from_chunks(mock_chunks)

        result = await chunk_relevancy_sorter.run("test input", mock_chunks, config)

        assert isinstance(result, ChunkRelevancySorterResult)
        assert result.content_chunks == mock_chunks
        mock_sort.assert_called_once_with("test input", mock_chunks, config)


@pytest.mark.asyncio
async def test_evaluate_chunks_relevancy(chunk_relevancy_sorter, mock_chunks, config):
    mock_relevancy = EvaluationMetricResult(
        value="high",
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        reason="Test reason",
    )

    with patch.object(
        chunk_relevancy_sorter, "_process_relevancy_evaluation"
    ) as mock_process:
        mock_process.return_value = ChunkRelevancy(
            chunk=mock_chunks[0], relevancy=mock_relevancy
        )

        result = await chunk_relevancy_sorter._evaluate_chunks_relevancy(
            "test input", mock_chunks, config
        )

        assert len(result) == len(mock_chunks)
        assert all(isinstance(r, ChunkRelevancy) for r in result)
        assert mock_process.call_count == len(mock_chunks)


@pytest.mark.asyncio
async def test_evaluate_chunk_relevancy(chunk_relevancy_sorter, mock_chunks, config):
    with patch(
        "unique_toolkit._common.chunk_relevancy_sorter.service.ContextRelevancyEvaluator.analyze"
    ) as mock_analyze:
        mock_analyze.return_value = EvaluationMetricResult(
            value="high",
            name=EvaluationMetricName.CONTEXT_RELEVANCY,
            reason="Test reason",
        )

        result = await chunk_relevancy_sorter._evaluate_chunk_relevancy(
            input_text="test input",
            chunk=mock_chunks[0],
            langugage_model=config.language_model,
            structured_output_config=config.structured_output_config,
            additional_llm_options=config.additional_llm_options,
        )

        assert isinstance(result, EvaluationMetricResult)
        assert result.value == "high"
        mock_analyze.assert_called_once()


@pytest.mark.asyncio
async def test_process_relevancy_evaluation_success(
    chunk_relevancy_sorter, mock_chunks, config
):
    with patch.object(
        chunk_relevancy_sorter, "_evaluate_chunk_relevancy"
    ) as mock_evaluate:
        mock_evaluate.return_value = EvaluationMetricResult(
            value="high",
            name=EvaluationMetricName.CONTEXT_RELEVANCY,
            reason="Test reason",
        )

        result = await chunk_relevancy_sorter._process_relevancy_evaluation(
            "test input", mock_chunks[0], config
        )

        assert isinstance(result, ChunkRelevancy)
        assert result.chunk == mock_chunks[0]
        assert result.relevancy is not None
        assert result.relevancy.value == "high"


@pytest.mark.asyncio
async def test_process_relevancy_evaluation_fallback(
    chunk_relevancy_sorter, mock_chunks, config
):
    with patch.object(
        chunk_relevancy_sorter, "_evaluate_chunk_relevancy"
    ) as mock_evaluate:
        # First call raises exception, second call succeeds
        mock_evaluate.side_effect = [
            Exception("Test error"),
            EvaluationMetricResult(
                value="medium",
                name=EvaluationMetricName.CONTEXT_RELEVANCY,
                reason="Test reason",
            ),
        ]

        with pytest.raises(ChunkRelevancySorterException):
            await chunk_relevancy_sorter._process_relevancy_evaluation(
                "test input", mock_chunks[0], config
            )


@pytest.mark.asyncio
async def test_validate_and_sort_relevant_chunks(
    chunk_relevancy_sorter, mock_chunks, config
):
    chunk_relevancies = [
        ChunkRelevancy(
            chunk=mock_chunks[0],
            relevancy=EvaluationMetricResult(
                value="low",
                name=EvaluationMetricName.CONTEXT_RELEVANCY,
                reason="Test reason",
            ),
        )
    ]
    chunk_relevancies.append(
        ChunkRelevancy(
            chunk=mock_chunks[1],
            relevancy=EvaluationMetricResult(
                value="medium",
                name=EvaluationMetricName.CONTEXT_RELEVANCY,
                reason="Test reason",
            ),
        )
    )
    chunk_relevancies.append(
        ChunkRelevancy(
            chunk=mock_chunks[2],
            relevancy=EvaluationMetricResult(
                value="high",
                name=EvaluationMetricName.CONTEXT_RELEVANCY,
                reason="Test reason",
            ),
        )
    )

    result = await chunk_relevancy_sorter._validate_and_sort_relevant_chunks(
        config, chunk_relevancies
    )

    assert isinstance(result, list)
    assert len(result) == len(mock_chunks)
    assert all(isinstance(relevancy.chunk, ContentChunk) for relevancy in result)
    assert result[0].chunk == mock_chunks[2]
    assert result[1].chunk == mock_chunks[1]
    assert result[2].chunk == mock_chunks[0]


@pytest.mark.asyncio
async def test_validate_chunk_relevancies_invalid(chunk_relevancy_sorter):
    invalid_relevancies = [
        ChunkRelevancy(
            chunk=ContentChunk(chunk_id="test", text="test", id="test", order=0),
            relevancy=None,
        )
    ]

    with pytest.raises(ChunkRelevancySorterException):
        await chunk_relevancy_sorter._validate_chunk_relevancies(invalid_relevancies)


def test_count_distinct_values(chunk_relevancy_sorter, mock_chunks):
    chunk_relevancies = [
        ChunkRelevancy(
            chunk=chunk,
            relevancy=EvaluationMetricResult(
                value="high",
                name=EvaluationMetricName.CONTEXT_RELEVANCY,
                reason="Test reason",
            ),
        )
        for chunk in mock_chunks[:2]
    ]
    chunk_relevancies.append(
        ChunkRelevancy(
            chunk=mock_chunks[2],
            relevancy=EvaluationMetricResult(
                value="medium",
                name=EvaluationMetricName.CONTEXT_RELEVANCY,
                reason="Test reason",
            ),
        )
    )

    value_counts = chunk_relevancy_sorter._count_distinct_values(chunk_relevancies)

    assert value_counts["high"] == 2
    assert value_counts["medium"] == 1
