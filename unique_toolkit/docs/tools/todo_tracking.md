# TODO Task Tracking

Agent-side task tracking that gives the model a persistent, visible TODO list for multi-step work. Inspired by the TodoWrite/TodoRead pattern in Claude Code.

## Why

Long agentic conversations lose track of progress. The model may repeat steps, skip items, or forget the overall plan. TODO tracking solves this by:

- Giving the model a structured task list it controls
- Attaching execution reminders to tool responses via `system_reminder` on `ToolCallResponse`
- Providing structured debug info for observability in the debug UI and terminal logs
- Supporting multi-step workflows (10-50+ steps) and batch operations (process ALL items)

## Architecture

```mermaid
sequenceDiagram
    participant Model
    participant UniqueAI
    participant TodoWriteTool
    participant ShortTermMemory
    participant HistoryManager
    participant TraceLogger

    Model->>UniqueAI: tool_call(todo_write, {todos, merge})
    UniqueAI->>TodoWriteTool: run(tool_call)
    TodoWriteTool->>ShortTermMemory: load current state
    ShortTermMemory-->>TodoWriteTool: TodoList | None
    TodoWriteTool->>TodoWriteTool: update or replace
    TodoWriteTool->>ShortTermMemory: save updated state (best-effort)
    TodoWriteTool-->>UniqueAI: ToolCallResponse (content + system_reminder + debug_info)

    Note over UniqueAI: HistoryManager appends system_reminder to tool message
    UniqueAI->>HistoryManager: add_tool_call_results()
    HistoryManager->>HistoryManager: content += system_reminder
    Note over UniqueAI: DebugInfoManager captures debug_info for UI
    UniqueAI->>UniqueAI: _log_tool_results (Steps panel entry)
    UniqueAI->>TraceLogger: log_tool_execution (system_reminders, todo state)
    Note over UniqueAI: After loop exits
    UniqueAI->>UniqueAI: _persist_debug_info (saves to message)
    UniqueAI->>TraceLogger: write_session_summary
    UniqueAI->>Model: messages (reminder visible in tool response history)
```

### How the reminder works

The `TodoWriteTool` sets `system_reminder` on its `ToolCallResponse`. The `HistoryManager` appends this reminder to the tool message content in the conversation history. This follows the same pattern used by sub-agent (a2a) tools. The model sees the reminder on all subsequent iterations because it persists in the conversation history.

When all items are terminal (completed/cancelled), the `system_reminder` is set to empty — no need to push autonomous execution when nothing remains.

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TodoStatus` | `unique_toolkit/agentic/tools/experimental/todo/schemas.py` | StrEnum: `pending`, `in_progress`, `completed`, `cancelled` |
| `TodoItem`, `TodoList`, `TodoWriteInput` | `unique_toolkit/agentic/tools/experimental/todo/schemas.py` | Pydantic data models |
| `TodoConfig` | `unique_toolkit/agentic/tools/experimental/todo/config.py` | Per-tool configuration with prompt defaults and overrides |
| `TodoWriteTool` | `unique_toolkit/agentic/tools/experimental/todo/service.py` | Tool implementation |
| `_inject_todo_tools` | `unique_orchestrator/unique_ai_builder.py` | Adds `todo_write` to space tools when enabled |
| `TraceLogger` | `unique_orchestrator/trace_logger.py` | Per-iteration trace logging for debugging |

## Enabling

Enable via the Experimental config in the admin UI (Loop Agent Configuration > TODO Tracking), or programmatically:

```python
# In ExperimentalConfig
from unique_toolkit.agentic.tools.experimental.todo.config import TodoConfig

experimental = ExperimentalConfig(
    todo_tracking=TodoConfig()  # uses built-in prompt defaults
)
```

The tool is dynamically injected at runtime when `todo_tracking` is active. If not enabled, the feature is completely dormant.

## Configuration

`TodoConfig` (defined in the toolkit, imported directly by the orchestrator) extends `BaseToolConfig`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `memory_key` | `str` | `"agent_todo_state"` | ShortTermMemory key for persisting state |
| `system_prompt` | `str` | Built-in prompt | System prompt injected for todo tracking. Edit to customize the agent's task tracking behavior. |
| `execution_reminder` | `str` | Built-in prompt | Execution-phase reminder appended to tool responses. Keeps the agent working autonomously until all items are done. |

There is no artificial limit on the number of todo items. Multi-step workflows and batch operations may have 50+ items, and all are preserved.

### Customizing Prompts

Both the system prompt (injected into the system message) and the execution reminder (appended to every `todo_write` response with active items) can be overridden from the admin UI. This enables experimentation without code changes.

Example: to make todo usage mandatory for batch tasks:

```python
TodoConfig(
    system_prompt="You MUST use todo_write for ANY task. No exceptions.",
    execution_reminder="Continue working. Do not stop.",
)
```

The built-in defaults are designed for GPT-5.4 and establish a two-phase workflow (clarification → autonomous execution). Different models may need different prompts — the override mechanism supports this.

## Tool Behavior

### TodoWriteTool (`todo_write`)

Accepts a list of `TodoItem` objects and a `merge` flag:

- **`merge=True`** (default): Updates existing items by ID, appends new ones, preserves items not mentioned in the call.
- **`merge=False`**: Replaces the entire list.

After update/replace, the state is saved to ShortTermMemory. Returns a formatted summary.

Each `TodoItem` has:
- `id` -- model-generated, free-form string identifier (e.g. `"research-apis"`, `"step-1"`)
- `content` -- task description
- `status` -- a `TodoStatus` value: `pending`, `in_progress`, `completed`, `cancelled`

### Status Icons

```
[ ] pending
[>] in_progress
[x] completed
[-] cancelled
```

### Autonomous Execution

The system prompt encourages liberal use of `todo_write` — any task involving 2+ tool calls should use it, since the user sees the task list as a live progress indicator. The threshold is deliberately low: it's better to track a simple task than to forget items in a complex one.

The prompt establishes a two-phase workflow:

1. **Clarification Phase** (before creating the task list): Ask all clarifying questions in a single message upfront.
2. **Execution Phase** (after creating the task list): Execute every step autonomously without stopping. No follow-up questions. Sensible defaults for ambiguous details.

Execution rules enforced by the prompt:
- After creating a task list, execute each step immediately
- Work through ALL items until every item is in a terminal state
- Do not ask the user for confirmation between steps
- When working on multiple items in parallel, mark all of them as `in_progress` — not limited to one at a time
- Combine `todo_write` with work tool calls in the same response — don't waste separate iterations on bookkeeping
- Do NOT summarize remaining items or ask if you should continue
- Only stop for hard blockers (missing credentials, nonexistent resources, unrecoverable errors)

Completion rules enforced by the prompt:
- Before writing a final response, call `todo_write` one last time to mark all remaining items as completed or cancelled — the final list must have zero pending/in_progress items
- Never write a final response while items are still pending
- For complex tasks, include a final "verify and synthesize" item to ensure clean wrap-up

### Debug Info

The `todo_write` response includes structured `debug_info` for the debug UI:

```json
{
  "input": {
    "merge": true,
    "items": [{"id": "t1", "content": "Research APIs", "status": "pending"}]
  },
  "state": {
    "completed": 1,
    "in_progress": 1,
    "pending": 1,
    "cancelled": 0,
    "items": [...]
  },
  "iteration": 2
}
```

Terminal logging is also enhanced — `DEBUG` level logs the full input arguments, `INFO` level logs the resulting state.

### Debug Info in the UI

The orchestrator persists accumulated `debug_info` from all tools to the message's `debugInfo` field after every loop exit (including on error, as a best-effort save). This means the debug panel in the UI always shows which tools ran and their structured output.

Additionally, after tool execution, tools with `debug_info` get a summary entry in the Steps panel. For `todo_write` this shows the current item counts:

```
**todo_write** — 3 items (1 completed, 1 in_progress, 1 pending)
```

## Testing

### Unit Tests

`tests/agentic/tools/test_todo_service.py` -- tests covering:
- `TodoList.update()` logic (update, append, preserve)
- `TodoList.has_active_items()` and `status_counter()` logic
- `TodoWriteTool.run()` (create, update, replace, formatting)
- Large todo lists (100 items) preserved without truncation
- `debug_info` structure on tool response
- `system_reminder` set when active items, empty when all terminal
- Tool registration, config validation
- Configurable prompts (system_prompt, execution_reminder overrides)
- Multi-step workflow simulation (full lifecycle, mid-conversation additions)

`unique_orchestrator/tests/test_todo_injection.py` -- tests covering:
- `_inject_todo_tools` adds `todo_write` when enabled, skips when disabled
- No duplicate injection when tool already present
- Config passed directly (same instance) to tool
- `TodoConfig` defaults and overrides

`unique_orchestrator/tests/test_unique_ai_update_debug_info_for_tool_control.py` -- tests covering:
- `_persist_debug_info` always runs (not gated by tool-took-control)
- `_persist_debug_info` skips DeepResearch (case-sensitive check)
- `_persist_debug_info_best_effort` swallows errors
- `_build_debug_info_event` includes assistant metadata
- `_log_tool_results` creates Steps entries for tools with debug_info
- `_format_tool_result_summary` formats todo state and generic debug info

`unique_orchestrator/tests/test_trace_logger.py` -- tests covering:
- `_serialize` and `_strip_chunks` helpers (recursive chunk removal)
- TraceLogger disabled when no env var and non-dev mode
- TraceLogger enabled via `UNIQUE_AI_TRACE_DIR` or dev-mode auto-enable
- LLM call logging, tool execution logging with system_reminder extraction
- Session summary writing with model, timing, todo progression

## Debugging

### Trace Logging

Set `UNIQUE_AI_TRACE_DIR=/tmp/unique-ai-traces` to write per-iteration JSON files capturing the full agent flow. In dev mode (`ENV=local` or `ENV=dev`), tracing auto-enables to `/tmp/unique-ai-traces`.

Each agent run creates a timestamped session directory with:
- `iter-NNN-llm.json`: messages sent to LLM + model response (excluding content chunks)
- `iter-NNN-tools.json`: tool calls + responses, system_reminders extracted, todo state snapshots
- `session-summary.json`: iteration count, tools used, todo progression, timing, model

## Design Decisions

### Single config, imported directly

`TodoConfig` is defined in the toolkit (`unique_toolkit/agentic/tools/experimental/todo/config.py`) and imported directly by the orchestrator's `ExperimentalConfig`. This follows the same pattern established by the OpenFile tool — one source of truth for configuration, no mirroring.

### Prompt defaults on config

The built-in system prompt and execution reminder live as field defaults on `TodoConfig`. This means the admin UI shows the actual prompt text by default (editable), and the service code simply reads `self.config.system_prompt` without fallback logic.

### ShortTermMemory persistence (best-effort)

Persistence via `ShortTermMemory` is wrapped in `try/except`. If the save fails, the tool still works — the state lives in the in-memory cache and in the tool response (part of conversation history). The model sees its own previous `todo_write` responses and can continue tracking.

### No TodoReadTool

The LLM never used `todo_read` because `todo_write` already returns the full state in its response content. The tool is not shipped to avoid dead code.

### Iteration budget awareness

The prompt instructs the model about its limited iteration budget without referencing specific system prompt heading names (avoiding fragile coupling with the system prompt template). The system prompt template already passes `current_iteration` and `max_loop_iterations` as Jinja2 variables.

## Relationship with PlanningMiddleware

The codebase has an existing `PlanningMiddleware` (in `unique_toolkit/agentic/loop_runner/middleware/planning/`). These two features solve different problems and compose well together.

| Aspect | PlanningMiddleware | TODO Tools |
|---|---|---|
| Level of abstraction | Tactical (this iteration) | Strategic (overall task) |
| Who decides? | Always runs | Model decides when to use |
| Output | Free-text reasoning | Structured items with statuses |
| Memory | Ephemeral (conversation history) | Best-effort ShortTermMemory + conversation history |
| Without the other | Must infer progress from raw history | Model plans implicitly |

**Either feature works independently.** Together, the planning step sees the TODO state in the conversation history and can make better decisions about what to do next.

## Known Issue: ShortTermMemory Persistence

The `ShortTermMemory.create_async` API requires scoping by `chatId`, `messageId`, or `companyId`. During tool execution, the `messageId` available from the `ChatEvent` is the **user's** message ID. This can cause `InvalidRequestError` when `TodoWriteTool` tries to persist state.

### Current workaround

`TodoWriteTool.run()` wraps persistence calls in `try/except`. If the save fails, the tool still returns the formatted state and `system_reminder` to the LLM. The state is visible in the tool response (part of conversation history), so the model can track progress even without backend persistence.
