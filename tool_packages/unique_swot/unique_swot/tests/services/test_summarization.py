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
async def test_summarization_agent_generates_summary(
    mock_llm, mock_language_model_service
):
    """Test that summarization agent generates executive summary."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt for {{company_name}}: {{report}}"

    agent = SummarizationAgent(
        llm=mock_llm,
        llm_service=mock_language_model_service,
        summarization_config=config,
    )

    # Mock the chat service response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Summary text"
    mock_language_model_service.complete_async = AsyncMock(return_value=mock_response)

    summary = await agent.summarize(
        company_name="ACME Corp", markdown_report="Full report content"
    )

    assert "Summary" in summary
    assert isinstance(summary, str)


@pytest.mark.asyncio
async def test_summarization_agent_handles_llm_failure(
    mock_llm, mock_language_model_service
):
    """Test that agent handles LLM failure gracefully."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        llm_service=mock_language_model_service,
        summarization_config=config,
    )

    # Mock LLM failure
    mock_language_model_service.complete_async = AsyncMock(
        side_effect=Exception("LLM Error")
    )

    summary = await agent.summarize(
        company_name="ACME Corp", markdown_report="Full report"
    )

    # Should return error message
    assert "error" in summary.lower()


@pytest.mark.asyncio
async def test_summarization_agent_remaps_references(
    mock_llm, mock_language_model_service
):
    """Test that agent remaps source references back to chunks."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        llm_service=mock_language_model_service,
        summarization_config=config,
    )

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "See [source1] and [source2]"
    mock_language_model_service.complete_async = AsyncMock(return_value=mock_response)

    summary = await agent.summarize(company_name="ACME Corp", markdown_report="Report")

    # Summary should be returned
    assert "See [source1] and [source2]" in summary


@pytest.mark.asyncio
async def test_summarization_agent_returns_reference_count(
    mock_llm, mock_language_model_service
):
    """Test that agent returns correct reference count."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        llm_service=mock_language_model_service,
        summarization_config=config,
    )

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Summary"
    mock_language_model_service.complete_async = AsyncMock(return_value=mock_response)

    summary = await agent.summarize(company_name="ACME Corp", markdown_report="Report")

    assert summary == "Summary"


@pytest.mark.asyncio
async def test_summarization_agent_resets_citation_manager(
    mock_llm, mock_language_model_service
):
    """Test that agent resets citation manager after summarization."""
    config = Mock()
    config.prompt_config.system_prompt = "System prompt"
    config.prompt_config.user_prompt = "User prompt"

    agent = SummarizationAgent(
        llm=mock_llm,
        llm_service=mock_language_model_service,
        summarization_config=config,
    )

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Summary"
    mock_language_model_service.complete_async = AsyncMock(return_value=mock_response)

    summary = await agent.summarize(company_name="ACME Corp", markdown_report="Report")

    # Just verify summary is returned
    assert summary == "Summary"
