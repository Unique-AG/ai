import logging
from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

logger = logging.getLogger(__name__)

_DEFAULT_TOOL_DESCRIPTION = """\
Create or update a task list to track progress. Use for any task involving \
multiple steps — the user sees this as a live progress indicator.

Provide active_form (present continuous, e.g. "Searching documents") for \
each task — this is shown to the user as live status text.

Mark exactly one item in_progress at a time. Mark it completed immediately \
when done, then move to the next item. Do not batch completions."""

_DEFAULT_SYSTEM_PROMPT = """\
You have access to a task tracking tool (todo_write). Use it proactively \
to track progress on any non-trivial task. The user sees the task list as \
a live progress indicator, so using it helps even for moderately complex work.

## When to Use

- Complex multi-step tasks requiring 3 or more distinct steps
- Non-trivial tasks that require careful planning or multiple operations
- Batch operations: when asked to process ALL items matching a criteria \
(e.g. all emails, all documents, all entries), create a todo for each item \
so none are skipped
- User explicitly requests a task list or provides a numbered list of things to do
- After receiving new instructions — immediately capture requirements as tasks
- Any task where tracking progress prevents repeating or forgetting work

## When NOT to Use

- Simple single-step questions or quick lookups that need at most one tool call
- Purely conversational or informational requests (e.g. "What does git status do?")
- Trivial tasks completable in fewer than 3 steps

## Examples

- User: "Research competitor pricing and write a comparison" \
  -> Create tasks: research competitor A, research competitor B, \
compile comparison table, write summary
- User: "What's the capital of France?" \
  -> Do NOT use todo_write — simple factual question
- User: "Process all the invoices in the uploads folder" \
  -> Create one task per invoice so none are skipped
- User: "Update the API docs, fix the broken tests, and add the new endpoint" \
  -> Create 3 tasks matching the user's list

## Two-Phase Workflow

1. CLARIFICATION PHASE (before creating the task list): Ask ALL clarifying \
questions in a single message. Gather every piece of information you need upfront.
2. EXECUTION PHASE (after creating the task list): Execute every step \
autonomously without stopping. Do NOT ask follow-up questions. Use sensible \
defaults for any ambiguous detail — note the assumption and move on.

## Task Design

- Create specific, actionable items with clear outcomes
- Break complex tasks into 3-7 manageable steps
- Use clear, descriptive names and provide active_form for each item \
(e.g. content: "Search for pricing data", active_form: "Searching for pricing data")
- For complex tasks, include a final "verify and synthesize" item

## Execution Rules

- After creating a task list, execute each step IMMEDIATELY. Do NOT ask the \
user for confirmation between steps.
- Work through ALL items autonomously until every item is in a terminal state \
(completed or cancelled).
- Mark exactly ONE item as in_progress at a time. Complete it before starting \
the next one. Do not batch completions — mark each task completed immediately \
after finishing.
- After completing a task, check if follow-up tasks need to be added.
- When a detail is unclear, choose the most reasonable default rather than \
stopping to ask. Document your assumption.
- Do NOT summarize remaining items or ask if you should continue. Just keep going.
- The ONLY reason to stop mid-execution is a hard blocker: missing credentials, \
a required resource that does not exist, or an unrecoverable error.

## Completion Rules

- Before writing your final response, you MUST call todo_write one last time \
to mark every remaining item as completed or cancelled. Your final todo list \
must have ZERO pending or in_progress items.
- Never write a final response while items are still pending. If items remain, \
keep executing them.

## Iteration Budget

- You have a limited number of iterations. On the final iteration, all tools \
(including todo_write) are removed. You MUST mark all items completed/cancelled \
BEFORE that final iteration.
- Items that require only analysis or synthesis (no external tool) should be \
marked completed as soon as you have the data, even if you write the analysis \
in a later response."""

_DEFAULT_EXECUTION_REMINDER = """\
You are in the EXECUTION PHASE. Do NOT ask the user any questions or request \
confirmation. You MUST process every pending item — do not skip or summarize. \
Mark exactly one item in_progress, complete it, then move to the next. Do not \
batch completions. Do NOT write a final text response while items are still \
pending or in_progress — keep executing until every item reaches a terminal \
state (completed/cancelled), then call todo_write one final time before \
responding."""

_PARALLEL_TOOL_DESCRIPTION = """\
Create or update a task list to track progress. Use for any task involving \
multiple steps — the user sees this as a live progress indicator.

Provide active_form (present continuous, e.g. "Searching documents") for \
each task — this is shown to the user as live status text.

Mark items in_progress when starting, completed when done. You can mark \
multiple items in_progress if working on them in parallel."""

_PARALLEL_EXECUTION_RULES = """\
- When working on multiple items in parallel, mark ALL of them as in_progress \
— do not limit yourself to one at a time.
- Combine todo_write with work tool calls in the same response. For example, \
call todo_write (to update statuses) alongside your WebSearch or other tool \
calls — do not waste a separate turn on bookkeeping alone."""

_PARALLEL_EXECUTION_REMINDER = """\
You are in the EXECUTION PHASE. Do NOT ask the user any questions or request \
confirmation. You MUST process every pending item — do not skip or summarize. \
Always include a todo_write call alongside your work tool calls in the same \
response — mark items in_progress before executing and completed after. Do not \
use a separate turn just for status updates. Do NOT write a final text response \
while items are still pending or in_progress — keep executing until every item \
reaches a terminal state (completed/cancelled), then call todo_write one final \
time before responding."""

_SEQUENTIAL_EXECUTION_RULES = """\
- Mark exactly ONE item as in_progress at a time. Complete it before starting \
the next one. Do not batch completions — mark each task completed immediately \
after finishing."""


class TodoConfig(BaseToolConfig):
    """Configuration for the todo tracking tool.

    Prompt fields default to the built-in prompts. Edit via the admin UI
    (Experimental Settings) to customize the agent's task tracking behavior.
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

    def _is_default(self, field_name: str) -> bool:
        return getattr(self, field_name) == self.model_fields[field_name].default

    @property
    def effective_tool_description(self) -> str:
        if self.parallel_mode and self._is_default("tool_description"):
            return _PARALLEL_TOOL_DESCRIPTION
        if self.parallel_mode:
            logger.warning(
                "parallel_mode is enabled but tool_description was customized. "
                "Using custom value as-is."
            )
        return self.tool_description

    @property
    def effective_system_prompt(self) -> str:
        if not self.parallel_mode:
            return self.system_prompt
        target = _SEQUENTIAL_EXECUTION_RULES.strip()
        result = self.system_prompt.replace(
            target,
            _PARALLEL_EXECUTION_RULES.strip(),
        )
        if result == self.system_prompt and target not in self.system_prompt:
            logger.warning(
                "parallel_mode is enabled but the system_prompt was customized "
                "and no longer contains the sequential execution rules. "
                "Appending parallel execution rules to the end."
            )
            result = self.system_prompt + "\n\n" + _PARALLEL_EXECUTION_RULES.strip()
        return result

    @property
    def effective_execution_reminder(self) -> str:
        if self.parallel_mode and self._is_default("execution_reminder"):
            return _PARALLEL_EXECUTION_REMINDER
        if self.parallel_mode:
            logger.warning(
                "parallel_mode is enabled but execution_reminder was customized. "
                "Using custom value as-is."
            )
        return self.execution_reminder
