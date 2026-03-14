# Claude Agent SDK Integration

**Status:** Functional — demo-ready. Full integration with monorepo/node-chat pending.

---

## Overview

`ClaudeAgentRunner` is a runner in `unique_toolkit` that drives Anthropic's Claude Agent SDK
as a first-class agent type on the Unique platform.

**What it does:** Claude runs an autonomous ReAct loop (Reason → Act → Observe → repeat),
searches the company knowledge base, chains multiple tool calls, and streams its response
to the frontend in real time — all wired into the existing platform infrastructure with no
changes to the frontend or message bus.

**Validated:** Claude autonomously ran 3–5 KB searches, returned 0-indexed `[source0]`…
`[sourceN]` citations in structured markdown, created CSV files via Bash/Write tools,
and uploaded them as `unique://content/{id}` inline references in the chat response.

---

## Quick Start

Minimal config to enable Claude Agent SDK in a `UniqueAIConfig`:

```python
from unique_toolkit.agentic.claude_agent import ClaudeAgentConfig

# In UniqueAIConfig:
config.agent.experimental.claude_agent_config = ClaudeAgentConfig(
    model="claude-sonnet-4-6",
    scope_ids=["your_scope_id"],       # KB scopes to search
    enable_code_execution=True,         # allows Bash, Write, Edit, etc.
    enable_workspace_persistence=True,  # cross-turn memory via checkpoint zip
)
```

`claude_agent_config` is `None` by default — no existing assistant is affected.
Routing is explicit opt-in only; no auto-enable by model name (Decision B6).

---

## Architecture

### Routing (explicit opt-in)

```
UniqueAIConfig.agent.experimental.claude_agent_config = ClaudeAgentConfig(...)
    ↓
build_unique_ai()  →  _build_claude_agent()  →  ClaudeAgentRunner
```

### Turn lifecycle

```
ClaudeAgentRunner.run()
  │
  ├─ _setup_workspace()          → fetch checkpoint zip if persistence enabled
  ├─ _build_system_prompt()      → compose prompt via prompts.py
  ├─ _build_history()            → placeholder for structured history (planned)
  ├─ _build_options()            → build ClaudeAgentOptions: tools, env, MCP server
  ├─ _run_claude_loop()          → iterate SDK query() event stream
  │    ├─ text_delta             → modify_assistant_message_async(content) → AMQP → frontend
  │    ├─ AssistantMessage       → log tool_use blocks; ToolProgressReporter.notify_from_tool_call()
  │    └─ ResultMessage          → capture final text if no deltas streamed
  ├─ _upload_output_files()      → upload ./output/ files → get filename→content_id map
  ├─ inject_file_references_into_text() → replace ./output/ paths with unique://content/{id}
  ├─ _run_post_processing()      → EvaluationManager + PostprocessorManager (concurrent)
  ├─ modify_assistant_message_async(set_completed_at=True)
  └─ finally: _save_workspace_checkpoint() + _cleanup_workspace()
```

### Streaming

```
Claude SDK text_delta event
    → accumulated_text += delta
    → ChatService.modify_assistant_message_async(content=accumulated_text)
    → PATCH /message  →  AMQP  →  frontend
```

Per-delta streaming. Each PATCH carries the full accumulated text to date.
Call frequency matches OpenAI streaming — no backend changes needed.

### Tool progress (interleaved with text)

```
AssistantMessage(ToolUseBlock)
    → ToolProgressReporter.notify_from_tool_call()
    → publish("[⏳ Running search_knowledge_base...]")
    → ChatService.modify_assistant_message_async(content=...)
```

Tool progress fires immediately when Claude decides to use a tool — before the result
returns. The user sees interleaved output: text streaming + tool progress events.

### MCP Tools — unified `unique_platform` server

A single in-process MCP server named `unique_platform` is registered with the Claude SDK.
It exposes two tool categories:

**1. `search_knowledge_base` (direct)**
- Calls `ContentService.search_content_chunks()` in-process
- Returns 0-indexed source chunks matching the citation format in the system prompt
- Uses `folderIdPath CONTAINS` metadata filter — includes all nested subfolder content

**2. Platform proxy tools (dynamic)**
- Any MCP tool in `event.payload.mcp_servers` is auto-wrapped as a proxy
- Proxy calls `unique_sdk.MCP.call_tool_async()` — web search, custom connectors, and
  third-party tools all work automatically with zero additional code
- Graceful degradation: errors returned as text content; agent loop never crashes

### File Rendering

Claude saves output files to `./output/` and references them inline as markdown:

```
I created the chart. Here it is:
![sales chart](./output/chart.png)
```

After Claude's loop exits, the runner:

1. **Uploads** every file in `./output/` via `ContentService` → gets a `content_id` per file
2. **Replaces** `./output/filename` paths inline in the accumulated text via
   `inject_file_references_into_text()` → `unique://content/{id}`

Result in the final chat message:

```
I created the chart. Here it is:
![sales chart](unique://content/cont_abc123)
```

Same end result as the Responses API postprocessor — `unique://content/{id}` URL where
the user expects to see the file. No frontend changes needed.

### System prompt pipeline

```
build_system_prompt(PromptContext(
    model_name, date_string,
    custom_instructions,    ← per-assistant instructions
    user_metadata,
    history_text,
))
→ system_header + conversation_style + answer_style + reference_guidelines
  + html_rendering + custom_instructions_section + history_section
```

Intentionally lean: no tool descriptions (SDK auto-generates), no execution limits
(SDK uses `max_turns`). Skills via filesystem are planned but not yet activated.

---

## Module Map

| File | Purpose |
|---|---|
| `config.py` | `ClaudeAgentConfig` — 25+ fields; `build_tool_policy()` |
| `runner.py` | `ClaudeAgentRunner` — full turn lifecycle |
| `prompts.py` | System prompt builder; `PromptContext` dataclass |
| `history.py` | `format_history_as_text()` — platform messages → text for prompt |
| `mcp_tools.py` | `build_unique_mcp_server()` — KB direct + platform proxy |
| `generated_files.py` | `inject_file_references_into_text()` — replace ./output/ paths with unique:// |
| `workspace.py` | Workspace zip fetch/persist/cleanup; `upload_output_files()` |
| `streaming.py` | `run_claude_loop()` — SDK event loop, text streaming, tool progress |
| `__init__.py` | Public exports |

---

## Running Tests

```bash
# Unit tests — no credentials needed (CI-safe)
cd unique_toolkit
poetry run pytest tests/agentic/claude_agent/ -q \
  --ignore=tests/agentic/claude_agent/test_workspace_e2e.py \
  --ignore=tests/agentic/claude_agent/test_multiturn_e2e.py \
  --ignore=tests/agentic/claude_agent/test_integration.py
# Expected: 145+ passed

# Full E2E demo — requires .env.local (streaming + KB + file creation + inline refs)
set -a && source ../.env.local && set +a
poetry run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "full_e2e"

# Level 1 tests — ANTHROPIC_API_KEY only (real API, no platform)
poetry run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "L1"

# Interactive streaming demo
poetry run python examples/frameworks/claude_agent/demo_streaming.py --scenario code
```

---

## Environment Setup

Copy `.env.local.example` (repo root) to `.env.local` and fill in your values.
`.env.local` is gitignored — it will never be committed. The demo and integration tests
load it from repo root automatically.

| Variable | Required for | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | All tests + demo | Anthropic API key |
| `UNIQUE_APP_KEY` | L2 tests | Unique platform API key |
| `UNIQUE_APP_ID` | L2 tests | Unique app ID |
| `UNIQUE_API_BASE_URL` | L2 tests | Platform base URL |
| `UNIQUE_AUTH_COMPANY_ID` | L2 tests | Company ID for KB/MCP calls |
| `UNIQUE_AUTH_USER_ID` | L2 tests | User ID for KB/MCP calls |
| `UNIQUE_TEST_SCOPE_ID` | L2 KB tests | KB folder scope ID to search |
| `UNIQUE_TEST_CHAT_ID` | Full E2E test | Chat ID for workspace + file upload |

---

## Configuration Reference

`ClaudeAgentConfig` key fields:

| Concept | Field | Default |
|---|---|---|
| Model selection | `model`, `fallback_model` | `claude-sonnet-4-6` |
| Skills directory | `setting_sources` | `None` (not yet activated) |
| Workspace persistence | `enable_workspace_persistence` | `True` |
| MCP server | `build_unique_mcp_server()` — KB direct + platform proxy | auto |
| Permission mode | `permission_mode`, `scope_ids` | `"bypassPermissions"`, `[]` |
| Custom instructions | `custom_instructions` → system prompt section | `None` |
| Verbose logging | `verbose_logging` → `[claude-agent]` INFO log lines | `False` |
| Code execution | `enable_code_execution` → Bash/Write/Edit/Read/Glob/Grep | `False` |
| Cost cap | `max_budget_usd` | `2.0` USD |
| Turn limit | `max_turns` | `20` |

---

## Known SDK Issue — stdin Workaround

The Claude Agent SDK has a bug when MCP servers are registered: the string-prompt code
path calls `end_input()` immediately, closing stdin before MCP tool responses can be
written back. Workaround: wrap the prompt string in a single-yield async generator
`_prompt_iter()` in `runner.py`, which forces the SDK into the `stream_input()` code
path. See `runner.py` for the full comment. Worth reporting upstream.

---

## What's NOT Done Yet

Honest status for review — these are known gaps, not defects:

- **Structured history injection** — `HistoryManager` is injected but not wired.
  Conversation context is injected as plain text in the system prompt for MVP.
  Structured Anthropic-format message history is planned post-MVP.
- **Evaluation check list** — `EvaluationManager` receives an empty `[]` check list
  (not wired to real tool config). Evaluations run but always see no checks to execute.
- **ThinkingManager** — injected but not wired; placeholder in `runner.py`.
- **SDK Skills** — `setting_sources` is wired in `ClaudeAgentConfig` but not yet
  activated. Activating it will allow the agent to read `.claude/*.md` skill files.
- **Monorepo integration** — `ClaudeAgentRunner` is not yet wired in the node-chat
  message bus. This is the next step after CTO review.

---

## Tests

| File | Coverage |
|---|---|
| `test_config.py` | `ClaudeAgentConfig` validation, `build_tool_policy()` |
| `test_runner.py` | `_build_options()`, `_build_system_prompt()`, history wiring, routing |
| `test_prompts.py` | All system prompt sections, reference guidelines |
| `test_history.py` | History formatting, tool message rendering, truncation |
| `test_mcp_tools.py` | `build_unique_mcp_server()`, KB tool, proxy tool, 0-indexed sources |
| `test_generated_files.py` | `inject_file_references_into_text()` — 22 unit tests |
| `test_integration.py` | L1: streaming, KB MCP, schema, code exec, proxy degradation, tool progress. L2: real platform KB + full E2E |
