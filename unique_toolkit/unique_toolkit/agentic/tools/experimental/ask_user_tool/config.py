from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.elicitation import (
    ElicitationCancelledException,
    ElicitationDeclinedException,
    ElicitationExpiredException,
)

_DEFAULT_TOOL_DESCRIPTION = """
Ask the user a question through a structured form and block until they answer. Use whenever you need information, a decision, or confirmation before continuing correctly: clarifying questions, confirmation before destructive or irreversible work, missing parameters, or choosing among plausible options. Do not ask the user in normal chat text while this tool is available—call AskUser, wait for the result, then continue. If unsure which interpretation, scope, or value applies, call AskUser instead of guessing. Destructive actions must include an explicit confirmation field. Form and chat anchoring are handled for you; the call blocks until the user responds, declines, cancels, or times out.
""".strip()

_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = """
- If your next message would ask the user for information, a decision, or confirmation, call AskUser instead of writing the question in chat.
- If more than one reasonable reading of the request exists, call AskUser before acting—do not silently pick a default.
- Destructive or irreversible actions require an explicit confirmation field (e.g. boolean `confirm`) in `response_schema`.
""".strip()

_DEFAULT_MESSAGE_DESCRIPTION = "The question or prompt shown to the user"

_DEFAULT_RESPONSE_SCHEMA_DESCRIPTION = """
JSON Schema object (root type "object") for the form shown to the user; you construct it. Single string property for free-text; boolean for a confirmation; string + enum for one choice (dropdown); array with items.enum for choose-many. Mark needed fields required and add short property descriptions (shown as help text). Prefer one small form over many calls.
Examples:
    - free-text: {"type":"object","properties":{"answer":{"type":"string"}},"required":["answer"]};
    - confirm: {"type":"object","properties":{"confirm":{"type":"boolean"}},"required":["confirm"]};
    - choice: {"type":"object","properties":{"region":{"type":"string","enum":["EU","US"]}},"required":["region"]};
    - multi: {"type":"object","properties":{"topics":{"type":"array","items":{"type":"string","enum":["a","b"]}}}}.
""".strip()

_TIMEOUT_SECONDS_MIN = 1
_TIMOUT_SECONDS_MAX = 3600

_POLLING_SECONDS_MIN = 0.5
_POLLING_SECONDS_MAX = 60


class AskUserToolConfig(BaseToolConfig):
    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_DEFAULT_TOOL_DESCRIPTION.splitlines())
        ),
    ] = Field(
        default=_DEFAULT_TOOL_DESCRIPTION,
        description="Description shown to the model for this tool.",
    )

    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT.splitlines())
        ),
    ] = Field(
        default=_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Extra system guidance about when and how to use AskUser.",
    )

    message_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_DEFAULT_MESSAGE_DESCRIPTION.splitlines())
        ),
    ] = Field(
        default=_DEFAULT_MESSAGE_DESCRIPTION,
        description="Description of the `message` parameter shown to the model.",
        title="`message` tool input field description",
    )

    response_schema_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_DEFAULT_MESSAGE_DESCRIPTION.splitlines())
        ),
    ] = Field(
        default=_DEFAULT_RESPONSE_SCHEMA_DESCRIPTION,
        description="Description of the `response_schema` parameter shown to the model.",
        title="`response_schema` tool input field description",
    )

    declined_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(ElicitationDeclinedException.INSTRUCTION.splitlines())
        ),
    ] = Field(
        default=ElicitationDeclinedException.INSTRUCTION,
        description="Message returned to the model when the user declines the request.",
        title="Declined response",
    )

    cancelled_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(ElicitationCancelledException.INSTRUCTION.splitlines())
        ),
    ] = Field(
        default=ElicitationCancelledException.INSTRUCTION,
        description="Message returned to the model when the user cancels the request.",
        title="Cancelled response",
    )

    expired_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(ElicitationExpiredException.INSTRUCTION.splitlines())
        ),
    ] = Field(
        default=ElicitationExpiredException.INSTRUCTION,
        description="Message returned to the model when the request expires before the user responds.",
        title="Expired response",
    )

    timeout_seconds: Annotated[
        int,
        RJSFMetaTag.NumberWidget.updown(
            min=_TIMEOUT_SECONDS_MIN, max=_TIMOUT_SECONDS_MAX
        ),
    ] = Field(
        default=300,
        ge=_TIMEOUT_SECONDS_MIN,
        le=_TIMOUT_SECONDS_MAX,
        description="Maximum seconds to wait for the user to respond.",
    )
    poll_interval_seconds: Annotated[
        float,
        RJSFMetaTag.NumberWidget.updown(
            min=_POLLING_SECONDS_MIN, max=_POLLING_SECONDS_MAX, step=0.5
        ),
    ] = Field(
        default=1.0,
        ge=_POLLING_SECONDS_MIN,
        le=_POLLING_SECONDS_MAX,
        description="Seconds to wait between attempts when checking whether user has responded.",
    )
