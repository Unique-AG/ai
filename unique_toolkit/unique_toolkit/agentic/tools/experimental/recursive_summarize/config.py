from typing import Annotated

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.experimental.recursive_summarize.prompts import (
    SYSTEM_PROMPT_TEMPLATE,
    TOOL_DESCRIPTION_TEMPLATE,
    TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_TEMPLATE,
    TOOL_RESPONSE_DRAFT_SUMMARY_SECTION_TEMPLATE,
    TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT_TEMPLATE,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class ToolResponseSystemReminderConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=True,
        title="Enable Tool Response Reminder",
        description=(
            "When enabled, attach reminder text to each successful RecursiveSummarize "
            "tool response (independent of system-prompt citation instructions)."
        ),
    )

    system_reminder_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT_TEMPLATE.split("\n")) / 3)
        ),
    ] = Field(
        default=TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT_TEMPLATE,
        title="Tool Response System Reminder Prompt",
        description=(
            "Text sent as system_reminder on RecursiveSummarize tool responses when "
            "the reminder is enabled."
        ),
    )

    def get_reminder_prompt_for_summary(
        self,
        summary: str,
        *,
        summary_in_tool_content: bool = True,
    ) -> str:
        if not self.enabled:
            return ""
        if summary_in_tool_content:
            return self.system_reminder_prompt.strip()
        draft_section = TOOL_RESPONSE_DRAFT_SUMMARY_SECTION_TEMPLATE.format(
            summary=summary
        )
        return f"{draft_section}\n\n{self.system_reminder_prompt}"


class RecursiveSummarizeExperimentalFeatures(BaseModel):
    model_config = get_configuration_dict()

    tool_response_system_reminder: ToolResponseSystemReminderConfig = Field(
        default_factory=ToolResponseSystemReminderConfig,
        description="Tool response system reminder.",
    )


class RecursiveSummarizeConfig(BaseToolConfig):
    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Enable the RecursiveSummarize tool. When enabled, the agent can "
                "summarize large chat-uploaded documents via recursive map-reduce."
            ),
        ),
    ] = Field(
        default=False,
        description="Enable the RecursiveSummarize tool.",
    )

    display_name: str = Field(
        default="Summarize",
        description="Human-readable label shown in the Steps panel.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=TOOL_DESCRIPTION_TEMPLATE,
        description="Tool description passed to the language model.",
    )

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=5),
    ] = Field(
        default=SYSTEM_PROMPT_TEMPLATE,
        description="System prompt injected when this tool is enabled.",
    )

    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_TEMPLATE.split("\n")) / 3
            )
        ),
    ] = Field(
        default=TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_TEMPLATE,
        description="Tool format information for the system prompt.",
    )

    experimental_features: RecursiveSummarizeExperimentalFeatures = Field(
        default_factory=RecursiveSummarizeExperimentalFeatures,
        description="Experimental features.",
    )

    language_model: Annotated[
        LMI | None,
        RJSFMetaTag.SpecialWidget.hidden(),
    ] = Field(
        default=None,
        description="Language model used for summarization. Populated by the orchestrator.",
    )

    model_max_input_tokens: Annotated[
        int,
        RJSFMetaTag.SpecialWidget.hidden(),
    ] = Field(
        default=0,
        description="Model maximum input tokens. Populated by the orchestrator.",
    )

    model_max_output_tokens: Annotated[
        int,
        RJSFMetaTag.SpecialWidget.hidden(),
    ] = Field(
        default=0,
        description="Model maximum output tokens. Populated by the orchestrator.",
    )

    token_safety_factor: float = Field(
        default=0.78,
        ge=0.1,
        le=1.0,
        description=(
            "Fraction of the model input limit used for content packing. "
            "Absorbs tokenizer drift for non-OpenAI models."
        ),
    )

    output_reservation_tokens: int = Field(
        default=1024,
        ge=128,
        description="Tokens reserved for each map/reduce LLM response.",
    )

    num_workers: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Maximum parallel summarization calls per map step.",
    )

    max_recursion_levels: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum recursive reduce depth before failing.",
    )
