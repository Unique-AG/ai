# Claude Agent SDK Integration

`unique_toolkit/agentic/claude_agent/` — draft, under active development

---

## Overview

`ClaudeAgentRunner` is a runner in `unique_toolkit` that drives Anthropic's Claude Agent SDK
as a first-class agent type on the Unique platform.

**What it does:** Claude runs an autonomous ReAct loop (Reason → Act → Observe → repeat),
searches the company knowledge base, chains multiple tool calls, and streams its response
to the frontend in real time — all wired into the existing platform infrastructure with no
changes to the frontend or message bus.

**Validated:** Claude autonomously ran 3–5 KB searches, returned 0-indexed `[source0]`…
`[sourceN]` citations in structured markdown, and wrote a Word document artifact via
`python-docx` against the QA platform.

---

## Architecture

### Routing (explicit opt-in)

```
UniqueAIConfig.agent.experimental.claude_agent_config = ClaudeAgentConfig(...)
    ↓
build_unique_ai()  →  _build_claude_agent()  →  ClaudeAgentRunner
```

`ClaudeAgentConfig` is `None` by default — no existing assistant is affected. Routing
is explicit opt-in only; no auto-enable by model name.

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
  │    ├─ AssistantMessage       → log tool_use blocks; parse TodoWrite state
  │    └─ ResultMessage          → capture final text if no deltas streamed
  ├─ _run_post_processing()      → EvaluationManager + PostprocessorManager (concurrent)
  ├─ modify_assistant_message_async(set_completed_at=True)
  └─ finally: _persist_workspace() + _cleanup_workspace()
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
| `generated_files.py` | Stub — `parse_references()`, artifact tracking |
| `workspace.py` | Stub — workspace zip fetch/persist |
| `streaming.py` | Stub — reserved for future streaming helpers |
| `__init__.py` | Public exports |

---

## Quick Start

### Streaming demo

The demo script lives at `examples/frameworks/claude_agent/demo_streaming.py`. It loads
credentials from `.env.local` at **repo root** — no need to `source` before running.

```bash
# 1. Set up credentials (repo root)
cp .env.local.example .env.local
# Edit .env.local — at minimum: ANTHROPIC_API_KEY
# For KB/code scenarios: add UNIQUE_APP_KEY, UNIQUE_APP_ID, UNIQUE_API_BASE_URL,
#   UNIQUE_AUTH_COMPANY_ID, UNIQUE_AUTH_USER_ID, UNIQUE_TEST_SCOPE_ID

# 2. Run from unique_toolkit
cd unique_toolkit
uv run python examples/frameworks/claude_agent/demo_streaming.py
```

**Scenarios** (pre-configured query + config):

| Scenario | Command | What it does |
|----------|--------|---------------|
| `kb` (default) | `--scenario kb` | Multi-search KB analysis of Oklo Q3 2024 earnings call |
| `code` | `--scenario code` | KB research + write `demo_output/investment_analysis.md` |
| `web` | `--scenario web` | KB search + native WebSearch for Oklo/nuclear news |
| `reasoning` | `--scenario reasoning` | Complex multi-step analytical task (ReAct depth) |

**Optional flags** (can combine with any scenario):

- `--query "Your question"` — override the scenario query
- `--code-exec` — enable Bash/Write/Edit (file creation)
- `--web-search` — enable native WebSearch
- `--scope scope_xxx` — KB scope ID (default: `scope_eg5zj45yfe5vccqcgw0h939e`)
- `--no-scope` — search entire KB (no scope filter)

**Example:**

```bash
cd unique_toolkit
uv run python examples/frameworks/claude_agent/demo_streaming.py --scenario code
uv run python examples/frameworks/claude_agent/demo_streaming.py --query "Summarise the Morgan Stanley fund fact sheets" --web-search
```

**Expected output:** `[demo]` and `[claude-agent]` log lines (system prompt size, tool calls,
tool results), then streamed reply. Tool results appear as `[tool] ← result: N chunks | [file1, ...]`.

### Integration tests

Credentials are loaded from `.env.local` at repo root (or `.local-dev/unique.env.qa` as fallback).
No need to `source` if that file exists.

```bash
cd unique_toolkit

# Level 1 — ANTHROPIC_API_KEY only (no platform connection):
uv run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "L1"

# Level 2 — real platform KB search (requires full .env.local with UNIQUE_* + UNIQUE_TEST_SCOPE_ID):
uv run pytest tests/agentic/claude_agent/test_integration.py::test_L2_kb_search_real_platform -v -s

# Unit tests only (CI-safe, no API key needed):
uv run pytest tests/agentic/claude_agent/ --ignore=tests/agentic/claude_agent/test_integration.py -v
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
| `UNIQUE_TEST_SCOPE_ID` | L2 KB test | KB folder scope ID to search |

---

## Configuration Reference

`ClaudeAgentConfig` key fields:

| Concept | Field | Default |
|---|---|---|
| Model selection | `model`, `fallback_model` | `claude-sonnet-4-20250514` |
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

## Current Limitations

- **Tool call visibility:** Only the final assistant message is streamed to the frontend.
  Intermediate tool calls (e.g. KB searches, file writes) are logged but not shown to the
  user during the loop. Planned enhancement.
- **Conversation history:** History is injected as a flat text block in the system prompt.
  Structured Anthropic-format message history is planned.
- **Workspace persistence:** `workspace.py` is a stub. Zip fetch/persist will be
  implemented once the workspace infrastructure is in place.
- **SDK Skills:** `setting_sources` is wired in `ClaudeAgentConfig` but not yet activated.
  Activating it will allow the agent to read `.claude/*.md` skill files on demand.

---

## Tests

| File | Coverage |
|---|---|
| `test_config.py` | `ClaudeAgentConfig` validation, `build_tool_policy()` |
| `test_runner.py` | `_build_options()`, `_build_system_prompt()`, history wiring, routing |
| `test_prompts.py` | All system prompt sections, reference guidelines |
| `test_history.py` | History formatting, tool message rendering, truncation |
| `test_mcp_tools.py` | `build_unique_mcp_server()`, KB tool, proxy tool, 0-indexed sources |
| `test_integration.py` | L1: streaming, KB MCP call, schema, code execution, proxy degradation. L2: real platform KB |
