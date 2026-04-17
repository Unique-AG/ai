from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.experimental.todo.prompts import (
    EXECUTION_REMINDER_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    TOOL_DESCRIPTION_TEMPLATE,
    VERIFICATION_NUDGE_TEMPLATE,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class TodoConfig(BaseToolConfig):
    display_name: str = Field(
        default="Progress",
        description="Human-readable label for task tracking shown in the Steps panel.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=TOOL_DESCRIPTION_TEMPLATE,
        description="Edit this Jinja template to customize the tool description passed to the LLM."
        "Available variable: parallel_mode (bool).",
    )

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=15),
    ] = Field(
        default=SYSTEM_PROMPT_TEMPLATE,
        description="Edit this Jinja template to customize the system prompt injected for task tracking. "
        "Available variable: parallel_mode (bool).",
    )

    execution_reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=5),
    ] = Field(
        default=EXECUTION_REMINDER_TEMPLATE,
        description="Edit this Jinja template to customize the reminder appended to tool responses "
        "during execution phase. Available variable: parallel_mode (bool).",
    )

    parallel_mode: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "When enabled, the agent may combine task tracking with other "
                "tool calls in the same turn and mark multiple items "
                "in_progress simultaneously. When disabled (default), the "
                "agent works through items one at a time with sequential "
                "status updates."
            ),
        ),
    ] = Field(
        default=False,
        title="Track tasks alongside other tool calls",
        description="Parallel Mode for Task Tracking",
    )

    show_triggered_tool_calls: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Show 'Triggered Tool Calls' entries in the Steps panel "
                "listing which tools the agent called each iteration. "
            ),
        ),
    ] = Field(
        default=True,
        title="Display triggered tool calls in the Steps panel",
        description="Display Triggered Tool Calls",
    )

    verification_threshold: int = Field(
        default=5,
        ge=0,
        title="Verification Nudge Threshold",
        description="After this many task completions, nudge the agent to verify its work "
        "before continuing. Set to 0 to disable.",
    )

    verification_nudge: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        default=VERIFICATION_NUDGE_TEMPLATE,
        description="Jinja template for the verification nudge message. "
        "Available variable: completed (int).",
    )
