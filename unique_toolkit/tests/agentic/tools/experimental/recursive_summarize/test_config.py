"""Tests for RecursiveSummarizeConfig."""

import pytest

from unique_toolkit.agentic.tools.experimental.recursive_summarize.config import (
    ToolResponseSystemReminderConfig,
)


class TestToolResponseSystemReminderConfig:
    @pytest.mark.ai
    def test_get_reminder_prompt_for_summary__citation_rules_only_when_summary_in_content(
        self,
    ) -> None:
        config = ToolResponseSystemReminderConfig(enabled=True)
        reminder = config.get_reminder_prompt_for_summary(
            "Key finding from the report."
        )

        assert "Key finding from the report." not in reminder
        assert "[sourceX]" in reminder
        assert "Draft summary" not in reminder

    @pytest.mark.ai
    def test_get_reminder_prompt_for_summary__includes_draft_when_not_in_content(
        self,
    ) -> None:
        config = ToolResponseSystemReminderConfig(enabled=True)
        reminder = config.get_reminder_prompt_for_summary(
            "Key finding from the report.",
            summary_in_tool_content=False,
        )

        assert "Key finding from the report." in reminder
        assert "Draft summary" in reminder

    @pytest.mark.ai
    def test_get_reminder_prompt_for_summary__empty_when_disabled(self) -> None:
        config = ToolResponseSystemReminderConfig(enabled=False)

        assert config.get_reminder_prompt_for_summary("ignored") == ""
