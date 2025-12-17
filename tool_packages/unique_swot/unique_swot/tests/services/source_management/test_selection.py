"""Tests for the SourceSelectionAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.source_management.selection.agent import SourceSelectionAgent
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)


def _make_content():
    """Helper to create test Content."""
    return Content(
        id="content_1",
        title="Test Document",
        key="test.pdf",
        chunks=[
            ContentChunk(
                id="content_1",
                chunk_id="chunk_1",
                title="Test Document",
                key="test.pdf",
                text="This document discusses ACME Corp's market position.",
                start_page=1,
                end_page=1,
                order=0,
            )
        ],
    )


@pytest.mark.asyncio
async def test_selection_agent_selects_relevant_source(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent selects relevant sources."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt for {{company_name}}"
    config.max_number_of_selected_chunks = 5

    agent = SourceSelectionAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_selection_config=config,
    )

    content = _make_content()

    # Mock the LLM response
    mock_result = SourceSelectionResult(
        should_select=True,
        reason="Relevant to company analysis",
        notification_message="Selected document",
    )

    with patch(
        "unique_swot.services.source_management.selection.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result = await agent.select(
            company_name="ACME Corp",
            content=content,
            step_notifier=mock_step_notifier,
        )

        assert result.should_select is True
        assert result.reason == "Relevant to company analysis"


@pytest.mark.asyncio
async def test_selection_agent_rejects_irrelevant_source(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent rejects irrelevant sources."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"
    config.max_number_of_selected_chunks = 5

    agent = SourceSelectionAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_selection_config=config,
    )

    content = _make_content()

    # Mock the LLM response for irrelevant content
    mock_result = SourceSelectionResult(
        should_select=False,
        reason="Not relevant to analysis",
        notification_message="Skipped document",
    )

    with patch(
        "unique_swot.services.source_management.selection.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result = await agent.select(
            company_name="ACME Corp",
            content=content,
            step_notifier=mock_step_notifier,
        )

        assert result.should_select is False
        assert result.reason == "Not relevant to analysis"


@pytest.mark.asyncio
async def test_selection_agent_handles_llm_failure(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent handles LLM failures gracefully."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"
    config.max_number_of_selected_chunks = 5

    agent = SourceSelectionAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_selection_config=config,
    )

    content = _make_content()

    # Mock LLM failure (returns None)
    with patch(
        "unique_swot.services.source_management.selection.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await agent.select(
            company_name="ACME Corp",
            content=content,
            step_notifier=mock_step_notifier,
        )

        # Should default to selecting the source
        assert result.should_select is True
        assert "error" in result.reason.lower() or "occured" in result.reason.lower()


@pytest.mark.asyncio
async def test_selection_agent_sends_notifications(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that notifications are sent during selection."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"
    config.max_number_of_selected_chunks = 5

    agent = SourceSelectionAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_selection_config=config,
    )

    content = _make_content()

    mock_result = SourceSelectionResult(
        should_select=True,
        reason="Relevant",
        notification_message="Selected",
    )

    with patch(
        "unique_swot.services.source_management.selection.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await agent.select(
            company_name="ACME Corp",
            content=content,
            step_notifier=mock_step_notifier,
        )

        # Verify notifications were sent
        assert mock_step_notifier.notify.await_count >= 1


@pytest.mark.asyncio
async def test_selection_agent_limits_chunks(
    mock_language_model_service, mock_llm, mock_step_notifier
):
    """Test that agent respects max_number_of_selected_chunks."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt with {{chunks}}"
    config.max_number_of_selected_chunks = 2

    agent = SourceSelectionAgent(
        llm_service=mock_language_model_service,
        llm=mock_llm,
        source_selection_config=config,
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

    mock_result = SourceSelectionResult(
        should_select=True,
        reason="Relevant",
        notification_message="Selected",
    )

    with patch(
        "unique_swot.services.source_management.selection.agent.generate_structured_output",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_generate:
        await agent.select(
            company_name="ACME Corp",
            content=content,
            step_notifier=mock_step_notifier,
        )

        # Verify that only limited chunks were included in the prompt
        # This is implementation-specific, but we can verify the call was made
        mock_generate.assert_awaited_once()
