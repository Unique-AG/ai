"""Tests for the SummarizationAgent."""

from unittest.mock import AsyncMock, Mock

import pytest

from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.summarization.agent import SummarizationAgent


def _make_report_components():
    """Helper to create test SWOTReportComponents."""
    return SWOTReportComponents(
        strengths=[
            SWOTReportComponentSection(
                h2="Market Position",
                entries=[
                    SWOTReportSectionEntry(
                        preview="Strong brand",
                        content="Strong brand recognition [chunk_a]",
                    )
                ],
            )
        ],
        weaknesses=[
            SWOTReportComponentSection(
                h2="Operational Challenges",
                entries=[
                    SWOTReportSectionEntry(
                        preview="High costs", content="High operational costs [chunk_b]"
                    )
                ],
            )
        ],
        opportunities=[],
        threats=[],
    )


@pytest.mark.asyncio
async def test_summarization_agent_generates_summary(mock_llm, mock_chat_service):
    """Test that summarization agent generates executive summary."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt for {{company_name}}: {{report}}"

    agent = SummarizationAgent(
        llm=mock_llm,
        chat_service=mock_chat_service,
        summarization_config=config,
    )

    report_handler = Mock()
    report_handler.render_report.return_value = "Full report content"

    citation_manager = Mock()
    citation_manager.add_citations_to_report.return_value = "Report with citations"
    citation_manager.get_referenced_content_chunks.return_value = []
    citation_manager.get_citations_map.return_value = {
        "a": "[source1]",
        "b": "[source2]",
    }
    citation_manager.reset_maps.return_value = None

    # Mock the chat service response
    mock_response = Mock()
    mock_response.message.text = "Summary text"
    mock_response.message.original_text = "Summary with [source1] and [source2]"
    mock_chat_service.complete_with_references_async = AsyncMock(
        return_value=mock_response
    )

    start_text, summary, num_refs = await agent.summarize(
        company_name="ACME Corp",
        result=_make_report_components(),
        citation_manager=citation_manager,
        report_handler=report_handler,
    )

    assert "Summary" in summary
    assert num_refs == 2
    assert isinstance(start_text, str)


@pytest.mark.asyncio
async def test_summarization_agent_handles_llm_failure(mock_llm, mock_chat_service):
    """Test that agent handles LLM failure gracefully."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        chat_service=mock_chat_service,
        summarization_config=config,
    )

    report_handler = Mock()
    report_handler.render_report.return_value = "Full report"

    citation_manager = Mock()
    citation_manager.add_citations_to_report.return_value = "Report"
    citation_manager.get_referenced_content_chunks.return_value = []

    # Mock LLM failure
    mock_chat_service.complete_with_references_async = AsyncMock(
        side_effect=Exception("LLM Error")
    )

    start_text, summary, num_refs = await agent.summarize(
        company_name="ACME Corp",
        result=_make_report_components(),
        citation_manager=citation_manager,
        report_handler=report_handler,
    )

    # Should return error message in start_text, summary is empty
    assert "error" in start_text.lower()
    assert summary == ""
    assert num_refs == 0


@pytest.mark.asyncio
async def test_summarization_agent_remaps_references(mock_llm, mock_chat_service):
    """Test that agent remaps source references back to chunks."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        chat_service=mock_chat_service,
        summarization_config=config,
    )

    report_handler = Mock()
    report_handler.render_report.return_value = "Report"

    citation_manager = Mock()
    citation_manager.add_citations_to_report.return_value = "Report"
    citation_manager.get_referenced_content_chunks.return_value = []
    citation_manager.get_citations_map.return_value = {
        "abc": "[source1]",
        "def": "[source2]",
    }
    citation_manager.reset_maps.return_value = None

    mock_response = Mock()
    mock_response.message.text = "Summary"
    mock_response.message.original_text = "See [source1] and [source2]"
    mock_chat_service.complete_with_references_async = AsyncMock(
        return_value=mock_response
    )

    _, summary, _ = await agent.summarize(
        company_name="ACME Corp",
        result=_make_report_components(),
        citation_manager=citation_manager,
        report_handler=report_handler,
    )

    # References should be remapped
    assert "[chunk_abc]" in summary
    assert "[chunk_def]" in summary


@pytest.mark.asyncio
async def test_summarization_agent_returns_reference_count(mock_llm, mock_chat_service):
    """Test that agent returns correct reference count."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        chat_service=mock_chat_service,
        summarization_config=config,
    )

    report_handler = Mock()
    report_handler.render_report.return_value = "Report"

    citation_manager = Mock()
    citation_manager.add_citations_to_report.return_value = "Report"
    citation_manager.get_referenced_content_chunks.return_value = []
    citation_manager.get_citations_map.return_value = {
        str(i): f"[source{i}]" for i in range(42)
    }
    citation_manager.reset_maps.return_value = None

    mock_response = Mock()
    mock_response.message.text = "Summary"
    mock_response.message.original_text = "Summary"
    mock_chat_service.complete_with_references_async = AsyncMock(
        return_value=mock_response
    )

    _, _, num_refs = await agent.summarize(
        company_name="ACME Corp",
        result=_make_report_components(),
        citation_manager=citation_manager,
        report_handler=report_handler,
    )

    assert num_refs == 42


@pytest.mark.asyncio
async def test_summarization_agent_resets_citation_manager(mock_llm, mock_chat_service):
    """Test that agent resets citation manager after summarization."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        chat_service=mock_chat_service,
        summarization_config=config,
    )

    report_handler = Mock()
    report_handler.render_report.return_value = "Report"

    citation_manager = Mock()
    citation_manager.add_citations_to_report.return_value = "Report"
    citation_manager.get_referenced_content_chunks.return_value = []
    citation_manager.get_citations_map.return_value = {}
    citation_manager.reset_maps = Mock()

    mock_response = Mock()
    mock_response.message.text = "Summary"
    mock_response.message.original_text = "Summary"
    mock_chat_service.complete_with_references_async = AsyncMock(
        return_value=mock_response
    )

    await agent.summarize(
        company_name="ACME Corp",
        result=_make_report_components(),
        citation_manager=citation_manager,
        report_handler=report_handler,
    )

    # Citation manager should be reset
    citation_manager.reset_maps.assert_called_once()
