from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_TOOL_DESCRIPTION = """REQUIRED whenever the user must supply information, confirm intent, or resolve ambiguity before you continue correctly. That includes: any clarifying question; any confirmation before destructive or irreversible work; missing identifiers or parameters; choosing among two or more plausible outcomes; structured fields (dates, enums, ratings); RAG/knowledge answers when multiple documents or chunks conflict or tie without a clear primary source.

FORBIDDEN: Do not ask the user anything in normal assistant message text while this tool is available—no "Could you clarify…?", bullet lists of options in chat, or follow-up questions in prose. If you need a reply, call AskUser first, wait for the tool result, then continue.

Default bias: if you are unsure which interpretation, document, scope, or parameter value applies, call AskUser instead of guessing.

Every AskUser call MUST include response_schema: a JSON Schema object (root type "object") describing the form fields shown in the UI. Never omit it. For free-text questions use a single required string property (e.g. answer). For confirmations use boolean(s); for fixed choices use string + enum (dropdown); for choose-many use array with items.enum (multi-checkbox). Treat non-success outcomes (DECLINED, CANCELLED, EXPIRED, local timeout, or confirm: false) as "do not proceed" unless the task explicitly allows retrying."""

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = """## AskUser — mandatory behavior

When this tool is enabled, treat user-directed questions as tool calls only.

**Hard rules**
- If your next assistant content would ask the user for information, a decision, or confirmation, you MUST call AskUser instead of writing that question in chat.
- If more than one reasonable reading of the request exists, or action correctness depends on a detail the user did not state, you MUST call AskUser before executing tools or giving a final grounded answer—do not silently pick a default.
- Destructive or irreversible actions MUST use AskUser with an explicit confirmation field in response_schema (typically boolean confirm).

**Always use AskUser**
- Ambiguous referents ("this", "the doc", "them") when execution or faithful RAG grounding depends on which entity.
- Two or more retrieved sources or chunks that disagree or are tied—ask which source/version/collection or how to reconcile.
- Any missing required argument for a subsequent tool call or workflow step.
- Explicit choose-one / choose-many among concrete options.
- Gathering structured input (enums, booleans, dates, numeric thresholds).

**May answer in chat without AskUser**
- Fully specified requests where no reasonable ambiguity remains.
- Purely educational or definitional explanations that do not commit to org-specific facts from retrieval.
- Brief progress narration with no question ("Searching the knowledge base…") where you are not requesting user input.

**RAG / knowledge chat**
- If retrieval returns multiple plausible documents or conflicting excerpts for the same claim, call AskUser before synthesizing a definitive answer—offer choices or ask which scope applies.
- Do not invent which policy, contract, or handbook applies when several match; ask.

The tool creates the elicitation in the UI and blocks until the user responds, declines, cancels, or the request expires/times out. Chat and assistant message anchoring are handled for you.

## Parameters

- message: The question or prompt shown to the user (required).
- tool_name: Short snake_case label for the request (default agent_question). Prefer meaningful names: confirm_delete, choose_region, pick_report, clarify_scope.
- response_schema: **Required** on every call — JSON Schema object for the form root (type object). You construct this schema; the tool implementation does not inject one.
- expires_in_seconds: Optional platform-side expiry if the user does not answer in time.

## Schema tips

- Set "required" for every field you truly need.
- Use enum for closed choices so the UI can render selectors.
- Use boolean for confirmations; treat true as go-ahead and anything else (including missing confirm or false) as stop for destructive work.
- Add short description strings on properties—they appear as help text.
- Prefer one small form over many sequential yes/no AskUser calls.

## Example response_schema shapes (enum dropdown + checkboxes)

Single choice (string + enum → dropdown):

{"type": "object", "properties": {"region": {"type": "string", "enum": ["EU", "US", "APAC"], "description": "Data region"}}, "required": ["region"]}

One confirmation checkbox (boolean):

{"type": "object", "properties": {"confirm": {"type": "boolean", "title": "Permanently delete", "description": "I understand this cannot be undone"}}, "required": ["confirm"]}

Multiple checkboxes (array + enum items → multi-select with checkboxes):

{"type": "object", "properties": {"topics": {"type": "array", "items": {"type": "string", "enum": ["billing", "security", "onboarding"]}, "description": "Topics to include"}}, "required": ["topics"]}

Free-text only:

{"type": "object", "properties": {"answer": {"type": "string", "description": "Your answer"}}, "required": ["answer"]}

## Reading the tool result

The tool returns JSON with elicitation_id, status, response (the user's submitted fields, when applicable), and timed_out.

| Status | Meaning | What to do |
|--------|---------|------------|
| RESPONDED / COMPLETED | User answered | Parse response JSON and continue. |
| DECLINED | User declined | Do not proceed; acknowledge and stop. |
| CANCELLED | Cancelled | Do not proceed. |
| EXPIRED | Expired on platform | Retry AskUser only if the task still needs the input. |
| timed_out true | Local wait limit hit | Do not assume an answer; retry only if appropriate. |

For destructive actions, proceed only when the response satisfies your schema (e.g. "confirm": true). Treat DECLINED, CANCELLED, EXPIRED, confirm false, and timeout as "stopped—tell the user you did not proceed."

Respect configured timeouts; extend timeout in agent settings only if users legitimately need more time."""


class ElicitUserToolConfig(BaseToolConfig):
    """Configuration for the AskUser (elicitation) tool."""

    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help="Enable the AskUser tool so the agent can elicit structured answers from the user.",
        ),
    ] = Field(
        default=False,
        description="Enable the AskUser elicitation tool.",
    )

    display_name: str = Field(
        default="Ask user",
        description="Human-readable label shown for this tool.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=14),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="Description shown to the model for this tool.",
    )

    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=28),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Extra system guidance about when and how to use AskUser.",
    )

    timeout_seconds: Annotated[
        int,
        RJSFMetaTag.NumberWidget.updown(min=1, max=3600),
    ] = Field(
        default=300,
        ge=1,
        le=3600,
        description="Maximum seconds to poll for a terminal elicitation status.",
    )

    poll_interval_seconds: Annotated[
        float,
        RJSFMetaTag.NumberWidget.updown(min=0.5, max=60.0, step=0.5),
    ] = Field(
        default=2.0,
        ge=0.5,
        le=60.0,
        description="Seconds between get_elicitation polls.",
    )
