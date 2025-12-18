"""Tests for the SourceIterationAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.source_management.iteration.agent import SourceIterationAgent
from unique_swot.services.source_management.iteration.schema import (
    SourceIterationResult,
    SourceIterationResults,
)


def _make_content(content_id="content_1", title="Test Doc"):
    """Helper to create test Content."""
    return Content(
        id=content_id,
        title=title,
        key=f"{title}.pdf",
        chunks=[
            ContentChunk(
                id=content_id,
                chunk_id="chunk_1",
                title=title,
                key=f"{title}.pdf",
                text=f"Content for {title}",
                start_page=1,
                end_page=1,
                order=0,
            )
        ],
    )


@pytest.mark.asyncio
async def test_iteration_agent_returns_ordered_sources(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent returns sources in LLM-specified order."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt with {{objective}}"
    # Use a template that includes the content IDs
    config.prompt_config.user_prompt = """
{% for content in contents %}
Source ID: {{ content.id }}
Title: {{ content.document_title }}
Chunks: {{ content.chunks }}
{% endfor %}
"""
    config.prompt_config.objective = "Sort by relevance"
    config.max_number_of_selected_chunks = 5

    agent = SourceIterationAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_iteration_config=config,
    )

    contents = [
        _make_content("c1", "Doc A"),
        _make_content("c2", "Doc B"),
        _make_content("c3", "Doc C"),
    ]

    # Mock LLM to return reversed order
    # Note: The IDs will be generated, so we need to capture them
    def capture_user_prompt(*args, **kwargs):
        # Extract IDs from the user prompt
        user_prompt = kwargs.get("user_message", "")
        import re

        ids = re.findall(r"content_[a-zA-Z0-9]+", user_prompt)

        # Ensure we have at least 3 IDs
        if len(ids) < 3:
            return SourceIterationResults(
                ordered_sources=[],
                results_summary="Not enough sources",
            )

        # Return ordered results (reversed)
        return SourceIterationResults(
            ordered_sources=[
                SourceIterationResult(id=ids[2], order=1),
                SourceIterationResult(id=ids[1], order=2),
                SourceIterationResult(id=ids[0], order=3),
            ],
            results_summary="Sorted by relevance",
        )

    with patch(
        "unique_swot.services.source_management.iteration.agent.generate_structured_output",
        new_callable=AsyncMock,
        side_effect=capture_user_prompt,
    ):
        iterator = await agent.iterate(
            contents=contents,
            step_notifier=mock_step_notifier,
        )

        # Collect results from async iterator
        results = []
        async for content in iterator:
            results.append(content)

        # Should return all 3 contents
        assert len(results) == 3
        # Order should be reversed (C, B, A)
        assert results[0].title == "Doc C"
        assert results[1].title == "Doc B"
        assert results[2].title == "Doc A"


@pytest.mark.asyncio
async def test_iteration_agent_handles_llm_failure(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent falls back to original order on LLM failure."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt with {{objective}}"
    config.prompt_config.user_prompt = """
{% for content in contents %}
Source ID: {{ content.id }}
{% endfor %}
"""
    config.prompt_config.objective = "Sort by relevance"
    config.max_number_of_selected_chunks = 5

    agent = SourceIterationAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_iteration_config=config,
    )

    contents = [
        _make_content("c1", "Doc A"),
        _make_content("c2", "Doc B"),
    ]

    # Mock LLM failure (returns None)
    with patch(
        "unique_swot.services.source_management.iteration.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=None,
    ):
        iterator = await agent.iterate(
            contents=contents,
            step_notifier=mock_step_notifier,
        )

        results = []
        async for content in iterator:
            results.append(content)

        # Should return all contents in original order
        assert len(results) == 2
        assert results[0].title == "Doc A"
        assert results[1].title == "Doc B"


@pytest.mark.asyncio
async def test_iteration_agent_handles_missed_documents(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent includes documents missed by LLM."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt with {{objective}}"
    config.prompt_config.user_prompt = """
{% for content in contents %}
Source ID: {{ content.id }}
{% endfor %}
"""
    config.prompt_config.objective = "Sort by relevance"
    config.max_number_of_selected_chunks = 5

    agent = SourceIterationAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_iteration_config=config,
    )

    contents = [
        _make_content("c1", "Doc A"),
        _make_content("c2", "Doc B"),
        _make_content("c3", "Doc C"),
    ]

    # Mock LLM to return only 2 documents (missing one)
    def return_partial_results(*args, **kwargs):
        user_prompt = kwargs.get("user_message", "")
        import re

        ids = re.findall(r"content_[a-zA-Z0-9]+", user_prompt)

        # Ensure we have at least 2 IDs
        if len(ids) < 2:
            return SourceIterationResults(
                ordered_sources=[],
                results_summary="Not enough sources",
            )

        # Only return first 2 IDs
        return SourceIterationResults(
            ordered_sources=[
                SourceIterationResult(id=ids[0], order=1),
                SourceIterationResult(id=ids[1], order=2),
            ],
            results_summary="Sorted",
        )

    with patch(
        "unique_swot.services.source_management.iteration.agent.generate_structured_output",
        new_callable=AsyncMock,
        side_effect=return_partial_results,
    ):
        iterator = await agent.iterate(
            contents=contents,
            step_notifier=mock_step_notifier,
        )

        results = []
        async for content in iterator:
            results.append(content)

        # Should return all 3 contents (missed one first, then ordered ones)
        assert len(results) == 3


@pytest.mark.asyncio
async def test_iteration_agent_sends_notifications(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that notifications are sent during iteration."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt with {{objective}}"
    config.prompt_config.user_prompt = """
{% for content in contents %}
Source ID: {{ content.id }}
{% endfor %}
"""
    config.prompt_config.objective = "Sort by relevance"
    config.max_number_of_selected_chunks = 5

    agent = SourceIterationAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_iteration_config=config,
    )

    contents = [_make_content("c1", "Doc A")]

    mock_result = SourceIterationResults(
        ordered_sources=[],
        results_summary="Sorted",
    )

    with patch(
        "unique_swot.services.source_management.iteration.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await agent.iterate(
            contents=contents,
            step_notifier=mock_step_notifier,
        )

        # Verify notifications were sent
        assert mock_step_notifier.notify.await_count >= 2  # Start and end


@pytest.mark.asyncio
async def test_iteration_agent_limits_chunks(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent respects max_number_of_selected_chunks."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt with {{objective}}"
    # Use a template that includes the chunks
    config.prompt_config.user_prompt = """
{% for content in contents %}
Source ID: {{ content.id }}
Title: {{ content.document_title }}
Content: {{ content.chunks }}
{% endfor %}
"""
    config.prompt_config.objective = "Sort by relevance"
    config.max_number_of_selected_chunks = 2

    agent = SourceIterationAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_iteration_config=config,
    )

    # Create content with many chunks
    content = Content(
        id="content_1",
        title="Test Document",
        key="test.pdf",
        chunks=[
            ContentChunk(
                id="content_1",
                chunk_id=f"chunk_{i}",
                title="Test Document",
                key="test.pdf",
                text=f"Chunk {i} content",
                start_page=i,
                end_page=i,
                order=i,
            )
            for i in range(10)
        ],
    )

    mock_result = SourceIterationResults(
        ordered_sources=[],
        results_summary="Sorted",
    )

    with patch(
        "unique_swot.services.source_management.iteration.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_generate:
        await agent.iterate(
            contents=[content],
            step_notifier=mock_step_notifier,
        )

        # Verify the call was made
        mock_generate.assert_awaited_once()

        # Check that the user prompt only includes limited chunks
        call_kwargs = mock_generate.call_args.kwargs
        user_prompt = call_kwargs["user_message"]
        # Should only have 2 chunks worth of content (Chunk 0 and Chunk 1)
        assert user_prompt.count("Chunk") == 2


@pytest.mark.asyncio
async def test_iteration_agent_empty_contents(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent handles empty contents list."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt with {{objective}}"
    config.prompt_config.user_prompt = "User prompt"
    config.prompt_config.objective = "Sort by relevance"
    config.max_number_of_selected_chunks = 5

    agent = SourceIterationAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_iteration_config=config,
    )

    mock_result = SourceIterationResults(
        ordered_sources=[],
        results_summary="No sources to sort",
    )

    with patch(
        "unique_swot.services.source_management.iteration.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        iterator = await agent.iterate(
            contents=[],
            step_notifier=mock_step_notifier,
        )

        results = []
        async for content in iterator:
            results.append(content)

        # Should return empty list
        assert len(results) == 0
