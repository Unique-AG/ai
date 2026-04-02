from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

_DEFAULT_TOOL_DESCRIPTION = "Create or update a task list to track progress. Use for any task involving multiple tool calls — the user sees this as a live progress indicator. Mark items in_progress when starting, completed when done. You can mark multiple items in_progress if working on them in parallel."

_DEFAULT_SYSTEM_PROMPT = """\
You have access to a task tracking tool (todo_write). Use it liberally — any task involving multiple tool calls should use todo_write to track progress. The user sees the task list as a live progress indicator, so using it is helpful even for moderately complex tasks.

When to use:
- Any task that will require 2 or more tool calls
- Multi-step workflows (research, analysis, document processing, comparisons)
- Batch operations: when asked to process ALL items matching a criteria (e.g. all emails, all documents, all entries), create a todo for each item so none are skipped
- Any task where tracking progress prevents repeating or forgetting work

When NOT to use:
- Simple single-step questions or quick lookups that need at most one tool call

Two-phase workflow:
1. CLARIFICATION PHASE (before creating the task list): Ask ALL clarifying questions in a single message. Gather every piece of information you need upfront.
2. EXECUTION PHASE (after creating the task list): Execute every step autonomously without stopping. Do NOT ask follow-up questions. Use sensible defaults for any ambiguous detail — note the assumption and move on.

Execution rules:
- After creating a task list, execute each step IMMEDIATELY. Do NOT ask the user for confirmation between steps.
- Work through ALL items autonomously until every item is in a terminal state (completed or cancelled).
- When working on multiple items in parallel, mark ALL of them as in_progress — do not limit yourself to one at a time.
- Combine todo_write with work tool calls in the same response. For example, call todo_write (to update statuses) alongside your WebSearch or other tool calls — do not waste a separate turn on bookkeeping alone.
- When a detail is unclear, choose the most reasonable default rather than stopping to ask. Document your assumption.
- Do NOT summarize remaining items or ask if you should continue. Just keep going.
- The ONLY reason to stop mid-execution is a hard blocker: missing credentials, a required resource that does not exist, or an unrecoverable error.

Completion rules:
- Before writing your final response, you MUST call todo_write one last time to mark every remaining item as completed or cancelled. Your final todo list must have ZERO pending or in_progress items.
- Never write a final response while items are still pending. If items remain, keep executing them.
- For complex tasks, include a final "verify and synthesize" item in your todo list to ensure a clean wrap-up.

Iteration budget:
- You have a limited number of iterations. On the final iteration, all tools (including todo_write) are removed. You MUST mark all items completed/cancelled BEFORE that final iteration.
- Items that require only analysis or synthesis (no external tool) should be marked completed as soon as you have the data, even if you write the analysis in a later response."""

_DEFAULT_EXECUTION_REMINDER = "You are in the EXECUTION PHASE. Do NOT ask the user any questions or request confirmation. You MUST process every pending item — do not skip or summarize. Always include a todo_write call alongside your work tool calls in the same response — mark items in_progress before executing and completed after. Do not use a separate turn just for status updates. Do NOT write a final text response while items are still pending or in_progress — keep executing until every item reaches a terminal state (completed/cancelled), then call todo_write one final time before responding."


class TodoConfig(BaseToolConfig):
    """Configuration for the todo tracking tool.

    Prompt fields default to the built-in prompts. Edit via the admin UI
    (Experimental Settings) to customize the agent's task tracking behavior.
    """

    display_name: str = Field(
        default="Progress",
        description="Human-readable label shown in the UI (Steps panel, tool progress).",
    )

    memory_key: str = Field(
        default="agent_todo_state",
        description="ShortTermMemory key under which TODO state is stored.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=_DEFAULT_TOOL_DESCRIPTION,
        description="Description passed to the LLM in the tool definition. "
        "Edit to change how the model understands when and how to use todo_write.",
    )

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=15),
    ] = Field(
        default=_DEFAULT_SYSTEM_PROMPT,
        description="System prompt injected for todo tracking. "
        "Edit to customize the agent's task tracking behavior.",
    )

    execution_reminder: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=5),
    ] = Field(
        default=_DEFAULT_EXECUTION_REMINDER,
        description="Reminder appended to tool responses during execution phase. "
        "Keeps the agent working autonomously until all items are done.",
    )
