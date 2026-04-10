from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.experimental.todo.prompts import (
    EXECUTION_REMINDER_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    TOOL_DESCRIPTION_TEMPLATE,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class TodoConfig(BaseToolConfig):
    """Configuration for the todo tracking tool.

    Prompt fields default to built-in Jinja templates that accept
    ``parallel_mode`` as a variable. Edit via the admin UI
    (Experimental Settings) to customize; custom values are also
    rendered as Jinja templates with the same context.
    """

    parallel_mode: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "When enabled, the agent may combine todo_write with other "
                "tool calls in the same turn and mark multiple items "
                "in_progress simultaneously. When disabled (default), the "
                "agent works through items one at a time with sequential "
                "status updates."
            ),
        ),
    ] = Field(
        default=False,
        description="Allow parallel todo updates alongside other tool calls.",
    )

    verification_threshold: int = Field(
        default=0,
        ge=0,
        description="After this many tasks complete without a verification step, "
        "nudge the agent to verify its work. Set to 0 to disable.",
    )

    display_name: str = Field(
        default="Progress",
        description="Human-readable label shown in the UI (Steps panel, tool progress).",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=TOOL_DESCRIPTION_TEMPLATE,
        description="Jinja template for the tool description passed to the LLM. "
        "Available variable: parallel_mode (bool).",
    )

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=15),
    ] = Field(
        default=SYSTEM_PROMPT_TEMPLATE,
        description="Jinja template for the system prompt injected for todo tracking. "
        "Available variable: parallel_mode (bool).",
    )

    execution_reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=5),
    ] = Field(
        default=EXECUTION_REMINDER_TEMPLATE,
        description="Jinja template for the reminder appended to tool responses "
        "during execution phase. Available variable: parallel_mode (bool).",
    )
