**Title:** `feat(toolkit-orchestrator): todo task tracking with configurable prompts`

## Summary

Add a `todo_write` tool that gives the LLM a structured, persistent task list for multi-step and batch work. When enabled, the agent creates, updates, and completes todo items as it works through a task — providing visible progress tracking and preventing forgotten or skipped steps.

Key capabilities:
- **Two-phase workflow**: the agent asks all clarifying questions upfront, then executes every step autonomously without stopping for confirmation
- **`system_reminder` on tool responses**: keeps the agent in execution mode until all items reach a terminal state — no orchestrator-level special-casing needed
- **Configurable prompts**: system prompt and execution reminder are editable directly in the admin UI under Experimental Settings, enabling prompt tuning without code changes
- **TraceLogger**: per-iteration JSON debug files (`iter-NNN-llm.json`, `iter-NNN-tools.json`, `session-summary.json`) for debugging agent message flow — auto-enables in dev mode
- **Structured `debug_info`**: status counts and item details visible in the UI debug panel and Steps panel

## How it works

1. Enable **Todo Tracking** in the space's Experimental Settings (toggle to "Active")
2. The agent receives todo tracking instructions in the system prompt
3. For multi-step tasks, the agent calls `todo_write` to create a task list, then works through items autonomously
4. Each `todo_write` response includes a `system_reminder` that keeps the agent executing until all items are completed/cancelled
5. Progress is visible in the UI via Steps panel entries and debug info

## Design decisions

- **No `TodoReadTool`**: the full state is returned in every `todo_write` response — a separate read tool was implemented in an earlier iteration and never called by the model
- **Config mirroring with parity test**: `TodoTrackingConfig` (orchestrator) mirrors `TodoConfig` (toolkit) for admin UI rendering without module-level toolkit imports. A unit test enforces field parity to prevent silent drift
- **Best-effort STM persistence**: todo state is persisted via `ShortTermMemory` (chat-scoped, no `messageId`). Failures are swallowed — the conversation history serves as implicit backup
- **Advisory usage model**: the prompt encourages liberal todo usage but doesn't mandate it for every task. The prompts are fully editable in the admin UI for experimentation

## What's included

### Toolkit (`unique_toolkit` → 1.65.0)
| File | Purpose |
|---|---|
| `agentic/tools/todo/schemas.py` | `TodoStatus`, `TodoItem`, `TodoList`, `TodoWriteInput` models |
| `agentic/tools/todo/config.py` | `TodoConfig` with prompt override fields |
| `agentic/tools/todo/service.py` | `TodoWriteTool` — run logic, state management, default prompts |
| `agentic/tools/todo/__init__.py` | ToolFactory registration |
| `docs/tools/todo_tracking.md` | Developer documentation |
| `tests/agentic/tools/test_todo_service.py` | 37 unit tests: schemas, service, config, multi-step workflows |

### Orchestrator (`unique_orchestrator` → 1.18.0)
| File | Purpose |
|---|---|
| `config.py` | `TodoTrackingConfig` in `ExperimentalConfig` with editable prompt defaults |
| `unique_ai_builder.py` | `_inject_todo_tools()` — dynamic tool injection when enabled |
| `trace_logger.py` | `TraceLogger` — per-iteration JSON debug files |
| `unique_ai.py` | `_persist_debug_info()`, `_log_tool_results()`, TraceLogger integration |
| `tests/test_todo_injection.py` | 8 tests: injection logic, config parity, prompt overrides |
| `tests/test_trace_logger.py` | 12 tests: serialization, enable/disable, system reminder extraction |
| `tests/test_unique_ai_update_debug_info_for_tool_control.py` | 12 tests: debug info persistence, Steps panel entries |

## Test plan

- [ ] Unit tests pass: 37 toolkit + 32 orchestrator (all new, no modifications to existing tests)
- [ ] Enable todo tracking in Experimental Settings and verify the config renders correctly
- [ ] System Prompt and Execution Reminder fields show the built-in prompts and are editable
- [ ] Send a multi-step task (e.g., "Research 5 competitors and write a comparison") and verify `todo_write` appears in tool calls
- [ ] Verify all todo items reach completed/cancelled state before the agent writes its final response
- [ ] Verify the agent works autonomously after creating the task list (no mid-execution questions)
- [ ] Disable todo tracking and verify the agent behaves identically to before (no `todo_write` tool injected)
- [ ] Check debug panel for `todo_write` debug info (status counts, item details)
