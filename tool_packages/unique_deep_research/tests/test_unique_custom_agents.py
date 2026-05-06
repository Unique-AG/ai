"""
Unit tests for unique_deep_research.unique_custom.agents module.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.runnables import RunnableConfig


@pytest.mark.ai
@pytest.mark.asyncio
async def test_final_report_generation__passes_date__to_report_cleanup_template() -> (
    None
):
    """
    Purpose: Verify final_report_generation passes the current date to the report_cleanup_prompt template render.
    Why this matters: Ensures the cleanup/refinement prompt includes date context so the LLM can produce temporally accurate reports.
    Setup summary: Mock get_today_str, TEMPLATE_ENV, get_engine_config, get_configurable_model, and ainvoke_with_token_handling;
                   assert the report_cleanup_prompt.j2 render call receives the date keyword argument.
    """
    from unique_deep_research.unique_custom.agents import final_report_generation

    fixed_date = "Thu Mar 5, 2026"

    # Arrange: build a minimal state dict
    state: Dict[str, Any] = {
        "notes": ["Finding A", "Finding B"],
        "research_brief": "Research AI trends in 2026",
        "messages": [],
    }
    config: RunnableConfig = {}

    mock_raw_report = Mock()
    mock_raw_report.content = "Raw report content"

    mock_refined_report = Mock()
    mock_refined_report.content = "Refined report content"

    # Mock engine config with model info
    mock_model_info = Mock()
    mock_model_info.name = "gpt-4o"
    mock_model_info.token_limits.token_limit_output = 10_000

    mock_custom_config = Mock()
    mock_custom_config.large_model = mock_model_info

    mock_llm = Mock()
    mock_llm.with_config.return_value = mock_llm

    # report_writer template mock (first get_template call)
    mock_writer_template = Mock()
    mock_writer_template.render.return_value = "Report writer prompt"

    # report_cleanup template mock (second get_template call)
    mock_cleanup_template = Mock()
    mock_cleanup_template.render.return_value = "Cleanup prompt content"

    def get_template_side_effect(name: str) -> Mock:
        if name == "report_cleanup_prompt.j2":
            return mock_cleanup_template
        return mock_writer_template

    with patch(
        "unique_deep_research.unique_custom.agents.get_today_str",
        return_value=fixed_date,
    ) as mock_get_today_str:
        with patch(
            "unique_deep_research.unique_custom.agents.TEMPLATE_ENV"
        ) as mock_template_env:
            mock_template_env.get_template.side_effect = get_template_side_effect
            with patch(
                "unique_deep_research.unique_custom.agents.get_engine_config",
                return_value=mock_custom_config,
            ):
                with patch(
                    "unique_deep_research.unique_custom.agents.get_configurable_model",
                    return_value=mock_llm,
                ):
                    with patch(
                        "unique_deep_research.unique_custom.agents.ainvoke_with_token_handling",
                        new=AsyncMock(
                            side_effect=[mock_raw_report, mock_refined_report]
                        ),
                    ):
                        with patch(
                            "unique_deep_research.unique_custom.agents.write_state_message_log"
                        ):
                            # Act
                            result = await final_report_generation(state, config)

    # Assert: result contains the refined report
    assert result["final_report"] == "Refined report content"

    # Assert: get_today_str was called (at least for the cleanup render)
    mock_get_today_str.assert_called()

    # Assert: report_cleanup_prompt.j2 render was called with date
    mock_cleanup_template.render.assert_called_once_with(date=fixed_date)
