# TODO Task Tracking

Agent-side task tracking that gives the model a persistent, visible TODO list for multi-step work. Inspired by the TodoWrite/TodoRead pattern in Claude Code.

## Why

Long agentic conversations lose track of progress. The model may repeat steps, skip items, or forget the overall plan. TODO tracking solves this by:

- Giving the model a structured task list it controls
- Attaching execution reminders to tool responses via `system_reminder` on `ToolCallResponse`
- Providing structured debug info for observability in the debug UI and terminal logs

## Architecture

```mermaid
sequenceDiagram
    participant Model
    participant UniqueAI
    participant TodoWriteTool
    participant ShortTermMemory
    participant HistoryManager

    Model->>UniqueAI: tool_call(todo_write, {todos, merge})
    UniqueAI->>TodoWriteTool: run(tool_call)
    TodoWriteTool->>ShortTermMemory: load current state
    ShortTermMemory-->>TodoWriteTool: TodoList | None
    TodoWriteTool->>TodoWriteTool: update or replace, truncate
    TodoWriteTool->>ShortTermMemory: save updated state (best-effort)
    TodoWriteTool-->>UniqueAI: ToolCallResponse (content + system_reminder + debug_info)

    Note over UniqueAI: HistoryManager appends system_reminder to tool message
    UniqueAI->>HistoryManager: add_tool_call_results()
    HistoryManager->>HistoryManager: content += system_reminder
    Note over UniqueAI: DebugInfoManager captures debug_info for UI
    UniqueAI->>UniqueAI: _log_tool_results (Steps panel entry)
    Note over UniqueAI: After loop exits
    UniqueAI->>UniqueAI: _persist_debug_info (saves to message)
    UniqueAI->>Model: messages (reminder visible in tool response history)
```

### How the reminder works

The `TodoWriteTool` sets `system_reminder` on its `ToolCallResponse`. The `HistoryManager` appends this reminder to the tool message content in the conversation history (line 191-192 of `history_manager.py`). This follows the same pattern used by sub-agent (a2a) tools. The model sees the reminder on all subsequent iterations because it persists in the conversation history.

When all items are terminal (completed/cancelled), the `system_reminder` is set to empty — no need to push autonomous execution when nothing remains.

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TodoStatus` | `unique_toolkit/agentic/tools/todo/schemas.py` | StrEnum: `pending`, `in_progress`, `completed`, `cancelled` |
| `TodoItem`, `TodoList`, `TodoWriteInput` | `unique_toolkit/agentic/tools/todo/schemas.py` | Pydantic data models |
| `TodoConfig` | `unique_toolkit/agentic/tools/todo/config.py` | Per-tool configuration |
| `TodoWriteTool` | `unique_toolkit/agentic/tools/todo/service.py` | Tool implementation |
| `TodoReadTool` | `unique_toolkit/agentic/tools/todo/service.py` | Read-only tool (not registered by default) |
| `_inject_todo_tools` | `unique_orchestrator/unique_ai_builder.py` | Adds `todo_write` to space tools when enabled |

## Enabling

Enable via the Experimental config in the admin UI (Loop Agent Configuration > TODO Tracking), or programmatically:

```python
# In ExperimentalConfig
experimental = ExperimentalConfig(
    todo_tracking=TodoTrackingConfig()  # uses defaults
)
```

The tool is dynamically injected at runtime when `todo_tracking` is active. If not enabled, the feature is completely dormant.

## Configuration

`TodoConfig` (and its mirror `TodoTrackingConfig` in the orchestrator) extends `BaseToolConfig`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `memory_key` | `str` | `"agent_todo_state"` | ShortTermMemory key for persisting state |
| `max_todos` | `int` | `20` (1-50) | Maximum items stored; excess is truncated |

## Tool Behavior

### TodoWriteTool (`todo_write`)

Accepts a list of `TodoItem` objects and a `merge` flag:

- **`merge=True`** (default): Updates existing items by ID, appends new ones, preserves items not mentioned in the call.
- **`merge=False`**: Replaces the entire list.

After update/replace, the list is truncated to `max_todos` and saved to ShortTermMemory. Returns a formatted summary.

Each `TodoItem` has:
- `id` -- model-generated, free-form string identifier (e.g. `"research-apis"`, `"step-1"`)
- `content` -- task description
- `status` -- a `TodoStatus` value: `pending`, `in_progress`, `completed`, `cancelled`

### TodoReadTool (`todo_read`)

Not registered by default. The LLM never used it because `todo_write` already returns the full state in its response content. Available for manual registration if needed.

### Status Icons

```
[ ] pending
[>] in_progress
[x] completed
[-] cancelled
```

### Autonomous Execution

The system prompt for `todo_write` includes explicit autonomous execution instructions:

- After creating a task list, execute each step immediately
- Do not ask the user for confirmation between steps
- Work through all items autonomously until complete or blocked
- Only stop to ask the user if genuinely blocked on information

The `system_reminder` on the tool response reinforces this: "Continue executing tasks autonomously."

### Debug Info

The `todo_write` response includes structured `debug_info` for the debug UI:

```json
{
  "input": {
    "merge": true,
    "items": [{"id": "t1", "content": "Research APIs", "status": "pending"}]
  },
  "state": {
    "total": 3,
    "completed": 1,
    "in_progress": 1,
    "pending": 1,
    "items": [...]
  },
  "iteration": 2
}
```

Terminal logging is also enhanced — `DEBUG` level logs the full input arguments, `INFO` level logs the resulting state.

### Debug Info in the UI

The orchestrator persists accumulated `debug_info` from all tools to the message's `debugInfo` field after every loop exit (including on error, as a best-effort save). This means the debug panel in the UI always shows which tools ran and their structured output — not just for tools that "take control" (like DeepResearch).

Additionally, after tool execution, tools with `debug_info` get a summary entry in the Steps panel. For `todo_write` this shows the current item counts:

```
**todo_write** — 3 items (1 completed, 1 in_progress, 1 pending)
```

## Testing

### Unit Tests

`tests/agentic/tools/test_todo_service.py` -- tests covering:
- `TodoList.update()` logic (update, append, preserve)
- `TodoList.has_active_items()` logic
- `TodoWriteTool.run()` (create, update, replace, truncate, formatting)
- `TodoReadTool.run()` (empty state, existing state)
- `debug_info` structure on tool response
- `system_reminder` set when active items, empty when all terminal
- Tool registration, config validation

`unique_orchestrator/tests/test_todo_injection.py` -- tests covering:
- `_inject_todo_tools` adds `todo_write` when enabled, skips when disabled
- `todo_read` not auto-registered
- Config fields (`inject_system_reminder`, `system_reminder_location`) removed

`unique_orchestrator/tests/test_unique_ai_update_debug_info_for_tool_control.py` -- tests covering:
- `_persist_debug_info` always runs (not gated by tool-took-control)
- `_persist_debug_info` skips DeepResearch (case-sensitive check)
- `_persist_debug_info_best_effort` swallows errors
- `_build_debug_info_event` includes assistant metadata
- `_log_tool_results` creates Steps entries for tools with debug_info
- `_format_tool_result_summary` formats todo state and generic debug info

### Multi-Step Workflow Tests

`tests/agentic/tools/test_todo_eval.py` -- scripted conversation simulations:
- Full lifecycle: pending -> in_progress -> completed across multiple iterations
- Update behavior with mid-conversation additions
- Truncation at max_todos boundary
- System-reminder on tool response validates active state tracking
- Iteration counter preserved across replace operations

### Manual QA Scenarios

Use these prompts in a real chat session with TODO tools enabled:

**Scenario 1: Multi-step research (should create todos)**
```
Compare the performance of Tesla, Apple, and Microsoft stock over the last year.
For each, provide key metrics, recent news, and your recommendation.
```
- Expect: 3+ todos created, progressive status updates, formatted list in responses.
- Verify: Debug panel shows `debug_info` with input/state structure.

**Scenario 2: Simple question (should NOT create todos)**
```
What's the current price of AAPL?
```
- Expect: Direct answer, no todo_write calls.

**Scenario 3: Autonomous execution (should NOT ask for confirmation)**
```
Research emerging market trends, compare with developed markets, and provide a recommendation.
```
- Expect: Model creates todos, then proceeds through each step without asking "shall I continue?".
- Verify: Terminal logs show each `TodoWriteTool` call with full state.

**What to check:**
- Tool calls visible in terminal logs (`TodoWriteTool: saved N items — Task list (...)`)
- Debug panel shows structured `debug_info` (input items, resulting state counts)
- `system_reminder` appears in tool response message history (drives autonomous execution)
- Status transitions follow `pending -> in_progress -> completed` lifecycle

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

### Why this works

The tool response containing the TODO state is part of the conversation history. On subsequent iterations, the LLM sees its own previous `todo_write` responses. This is effectively how Claude Code handles TODO state — it lives in the conversation context, not in an external database.
