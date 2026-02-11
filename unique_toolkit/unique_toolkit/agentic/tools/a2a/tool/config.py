import re
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import Field, field_validator
from pydantic.json_schema import SkipJsonSchema
from pydantic.main import BaseModel

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class SubAgentSystemReminderType(StrEnum):
    FIXED = "fixed"
    REGEXP = "regexp"
    REFERENCE = "reference"
    NO_REFERENCE = "no_reference"


T = TypeVar("T", bound=SubAgentSystemReminderType)


class SystemReminderConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict()

    type: T


_SYSTEM_REMINDER_FIELD_DESCRIPTION = """
The reminder to add to the tool response. The reminder can be a Jinja template and can contain the following placeholders:
- {{ display_name }}: The display name of the sub agent.
- {{ tool_name }}: The tool name. 
""".strip()


class NoReferenceSystemReminderConfig(SystemReminderConfig):
    """A system reminder that is only added if the sub agent response does not contain any references."""

    type: Literal[SubAgentSystemReminderType.NO_REFERENCE] = (
        SubAgentSystemReminderType.NO_REFERENCE
    )
    reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        default="Do NOT create any references from this sub agent in your response! The sub agent response does not contain any references.",
        description=_SYSTEM_REMINDER_FIELD_DESCRIPTION,
    )


class ReferenceSystemReminderConfig(SystemReminderConfig):
    type: Literal[SubAgentSystemReminderType.REFERENCE] = (
        SubAgentSystemReminderType.REFERENCE
    )
    reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        default="Rememeber to properly reference EACH fact from sub agent {{ display_name }}'s response with the correct format INLINE. You MUST COPY THE REFERENCE AS PRESENT IN THE SUBAGENT RESPONSE.",
        description=_SYSTEM_REMINDER_FIELD_DESCRIPTION,
    )


class FixedSystemReminderConfig(SystemReminderConfig):
    type: Literal[SubAgentSystemReminderType.FIXED] = SubAgentSystemReminderType.FIXED
    reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        description=_SYSTEM_REMINDER_FIELD_DESCRIPTION,
    )


_REGEXP_DETECTED_REMINDER_FIELD_DESCRIPTION = """
The reminder to add to the tool response. The reminder can be a Jinja template and can contain the following placeholders:
- {{ display_name }}: The display name of the sub agent.
- {{ tool_name }}: The tool name. 
- {{ text_matches }}: Will be replaced with the portions of the text that triggered the reminder.
""".strip()


class RegExpDetectedSystemReminderConfig(SystemReminderConfig):
    """A system reminder that is only added if the sub agent response matches a regular expression."""

    type: Literal[SubAgentSystemReminderType.REGEXP] = SubAgentSystemReminderType.REGEXP

    regexp: re.Pattern[str] = Field(
        description="The regular expression to use to detect whether the system reminder should be added.",
    )
    reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        description=_REGEXP_DETECTED_REMINDER_FIELD_DESCRIPTION,
    )


SystemReminderConfigType = (
    FixedSystemReminderConfig
    | RegExpDetectedSystemReminderConfig
    | ReferenceSystemReminderConfig
    | NoReferenceSystemReminderConfig
)

DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE = """
This is the message that will be sent to the sub-agent.
""".strip()


class SubAgentToolConfig(BaseToolConfig):
    model_config = get_configuration_dict()

    assistant_id: SkipJsonSchema[str] = Field(
        default="",
        description="The unique identifier of the assistant to use for the sub-agent.",
    )
    chat_id: SkipJsonSchema[str | None] = Field(
        default=None,
        description="The chat ID to use for the sub-agent conversation. If None, a new chat will be created.",
    )
    reuse_chat: Annotated[bool, RJSFMetaTag.BooleanWidget.checkbox()] = Field(
        default=True,
        description="Whether to reuse the existing chat or create a new one for each sub-agent call.",
    )
    use_sub_agent_references: Annotated[bool, RJSFMetaTag.BooleanWidget.checkbox()] = Field(
        default=True,
        description="Whether this sub agent's references should be used in the main agent's response.",
    )
    forced_tools: list[str] = Field(
        default=[],
        description="The list of tool names that will be forced to be called for this sub-agent.",
    )

    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=2
        ),
    ] = Field(
        default="",
        description="Description of the tool that will be included in the system prompt.",
    )
    tool_description: SkipJsonSchema[str] = Field(
        default="",
        description="Description of the tool that will be included in the tools sent to the model.",
    )
    param_description_sub_agent_user_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=2
        ),
    ] = Field(
        default=DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE,
        description="Description of the user message parameter that will be sent to the model.",
    )
    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=2
        ),
    ] = Field(
        default="",
        description="Format information that will be included in the system prompt to guide response formatting.",
    )
    tool_description_for_user_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=2
        ),
    ] = Field(
        default="",
        description="Description of the tool that will be included in the user prompt.",
    )
    tool_format_information_for_user_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=2
        ),
    ] = Field(
        default="",
        description="Format information that will be included in the user prompt to guide response formatting.",
    )

    poll_interval: Annotated[float, RJSFMetaTag.NumberWidget.updown(min=0.1, max=60, step=0.1)] = Field(
        default=1.0,
        description="Time interval in seconds between polling attempts when waiting for sub-agent response.",
    )
    max_wait: Annotated[float, RJSFMetaTag.NumberWidget.updown(min=1, max=600, step=1)] = Field(
        default=120.0,
        description="Maximum time in seconds to wait for the sub-agent response before timing out.",
    )
    stop_condition: Literal["stoppedStreamingAt", "completedAt"] = Field(
        default="completedAt",
        description="The condition that will be used to stop the polling for the sub-agent response.",
    )

    tool_input_json_schema: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        default="",
        description="A custom JSON schema to send to the llm as the tool input schema.",
    )

    @field_validator("tool_input_json_schema", mode="before")
    @classmethod
    def _coerce_none_to_empty(cls, v: str | None) -> str:
        """Backwards compatibility: existing configs may have null stored."""
        return v or ""

    returns_content_chunks: Annotated[bool, RJSFMetaTag.BooleanWidget.checkbox()] = Field(
        default=False,
        description="If set, the sub-agent response will be interpreted as a list of content chunks.",
    )

    system_reminders_config: list[
        Annotated[
            SystemReminderConfigType,
            Field(discriminator="type"),
        ]
    ] = Field(
        default=[],
        description="Configuration for the system reminders to add to the tool response.",
    )
