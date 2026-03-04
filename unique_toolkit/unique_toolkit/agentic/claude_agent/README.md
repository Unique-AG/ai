# Claude Agent SDK Integration

`unique_toolkit/agentic/claude_agent/` — Steps 1–4 (draft, architecture review)

---

## Overview

`ClaudeAgentRunner` is a new bypass runner in `unique_toolkit` that drives Anthropic's
Claude Agent SDK as a first-class agent type on the Unique platform.

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
is explicit opt-in only (Decision B6). No auto-enable by model name.

### Turn lifecycle

```
ClaudeAgentRunner.run()
  │
  ├─ _setup_workspace()          → fetch checkpoint zip if persistence enabled (Step 7)
  ├─ _build_system_prompt()      → compose prompt via prompts.py
  ├─ _build_history()            → placeholder for structured history (Step 6b)
  ├─ _build_options()            → build ClaudeAgentOptions: tools, env, MCP server
  ├─ _run_claude_loop()          → iterate SDK query() event stream
  │    ├─ text_delta             → modify_assistant_message_async(content) → AMQP → frontend
  │    ├─ AssistantMessage       → log tool_use blocks; parse TodoWrite state
  │    └─ ResultMessage          → capture final text if no deltas streamed
  ├─ _run_post_processing()      → EvaluationManager + PostprocessorManager (concurrent)
  ├─ modify_assistant_message_async(set_completed_at=True)
  └─ finally: _persist_workspace() + _cleanup_workspace()
```

### Streaming contract (Decision A2)

```
Claude SDK text_delta event
    → accumulated_text += delta
    → ChatService.modify_assistant_message_async(content=accumulated_text)
    → PATCH /message  →  AMQP  →  frontend
```

Per-delta streaming. Each PATCH carries the full accumulated text to date.
Confirmed with platform team: call frequency matches OpenAI streaming — no backend changes needed.

### MCP Tools — unified `unique_platform` server (Decision B10)

A single in-process MCP server named `unique_platform` is registered with the Claude SDK.
It exposes two tool categories:

**1. `search_knowledge_base` (direct)**
- Calls `ContentService.search_content_chunks()` in-process
- Returns 0-indexed source chunks matching the `_REFERENCE_GUIDELINES` citation format
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
    custom_instructions,    ← per-assistant instructions (Skills via filesystem: Step 5)
    user_metadata,
    history_text,
))
→ system_header + conversation_style + answer_style + reference_guidelines
  + html_rendering + custom_instructions_section + history_section
```

Mirrors Abi's `buildClaudeAgentSystemPrompt()` in Node exactly. Intentionally lean:
no tool descriptions (SDK auto-generates), no skills content injected (filesystem-based,
Step 5), no execution limits (SDK uses `max_turns`).

---

## Module Map

| File | Purpose |
|---|---|
| `config.py` | `ClaudeAgentConfig` — 25+ fields; `build_tool_policy()` |
| `runner.py` | `ClaudeAgentRunner` — full turn lifecycle |
| `prompts.py` | System prompt builder; `PromptContext` dataclass |
| `history.py` | `format_history_as_text()` — platform messages → text for prompt |
| `mcp_tools.py` | `build_unique_mcp_server()` — KB direct + platform proxy |
| `generated_files.py` | Stub — `parse_references()`, artifact tracking (Step 11) |
| `workspace.py` | Stub — workspace zip fetch/persist (Step 7) |
| `streaming.py` | Stub — reserved for future streaming helpers |
| `__init__.py` | Public exports |

---

## Quick Start

### Streaming demo (ANTHROPIC_API_KEY only)

```bash
# 1. Set up credentials
cp .env.local.example .env.local      # repo root
# Edit .env.local — fill in ANTHROPIC_API_KEY

# 2. Load env and run
cd unique_toolkit
set -a && source ../.env.local && set +a
poetry run python examples/frameworks/claude_agent/demo_streaming.py
```

Expected output: Claude answers a question about test-driven development, streamed
chunk by chunk to the terminal.

### Integration tests

```bash
cd unique_toolkit

# Level 1 — ANTHROPIC_API_KEY only (no platform connection):
set -a && source ../.env.local && set +a
poetry run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "L1"

# Level 2 — real QA platform KB search (requires full .env.local):
poetry run pytest tests/agentic/claude_agent/test_integration.py::test_L2_kb_search_real_platform -v -s

# Unit tests only (CI-safe, no API key needed):
poetry run pytest tests/agentic/claude_agent/ --ignore=tests/agentic/claude_agent/test_integration.py -v
```

---

## Environment Setup

Copy `.env.local.example` (repo root) to `.env.local` and fill in your values.
`.env.local` is gitignored — it will never be committed.

| Variable | Required for | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | All tests + demo | Anthropic API key |
| `UNIQUE_APP_KEY` | L2 tests | Unique platform API key (QA) |
| `UNIQUE_APP_ID` | L2 tests | Unique app ID (QA) |
| `UNIQUE_API_BASE_URL` | L2 tests | Platform base URL, e.g. `https://next.qa.unique.app/api` |
| `UNIQUE_AUTH_COMPANY_ID` | L2 tests | Company ID for KB/MCP calls |
| `UNIQUE_AUTH_USER_ID` | L2 tests | User ID for KB/MCP calls |
| `UNIQUE_TEST_SCOPE_ID` | L2 KB test | KB folder scope ID to search |

---

## Configuration Reference

`ClaudeAgentConfig` maps directly to the CTO architecture document (§9 Configuration):

| CTO doc concept | `ClaudeAgentConfig` field | Default |
|---|---|---|
| Model selection | `model`, `fallback_model` | `claude-sonnet-4-20250514` |
| Skills directory | `setting_sources` (Step 5 — wired, not activated) | `None` |
| Checkpoint restore | `enable_workspace_persistence` (Step 7) | `True` |
| MCP server list | `build_unique_mcp_server()` — KB direct + platform proxy | auto |
| Access settings | `permission_mode`, `scope_ids` | `"bypassPermissions"`, `[]` |
| Custom instructions | `custom_instructions` → `custom_instructions_section()` | `None` |
| Verbose trace | `verbose_logging` → `[claude-agent]` INFO log lines | `False` |
| Code execution | `enable_code_execution` → Bash/Write/Edit/Read/Glob/Grep tools | `False` |
| Cost cap | `max_budget_usd` | `2.0` USD |
| Turn limit | `max_turns` | `20` |

---

## SDK Finding — stdin Workaround

The Claude Agent SDK has a bug when MCP servers are registered: the string-prompt
code path calls `end_input()` immediately, closing stdin before MCP tool responses
can be written back. Workaround: wrap the prompt string in a single-yield async
generator `_prompt_iter()` in `runner.py` which forces the SDK into the
`stream_input()` code path. See `runner.py` comments. Worth reporting upstream.

---

## Status

### What works (Steps 1–4)

| Capability | Status |
|---|---|
| `ClaudeAgentRunner` — full turn lifecycle | Done |
| Streaming via `modify_assistant_message_async()` | Done — confirmed on QA |
| KB search (direct, 0-indexed citations) | Done — confirmed on QA |
| Platform MCP proxy (web search, custom connectors) | Done — graceful degradation confirmed |
| System prompt builder (mirrors Abi's Node implementation) | Done |
| History formatter (User/Assistant + tool messages) | Done |
| Evaluation + postprocessors after loop | Done |
| Orchestrator routing (`ExperimentalConfig.claude_agent_config`) | Done (reference only — PR 2) |
| 101 unit tests | Passing |
| L1 integration tests (SDK + mocked platform) | Passing |
| L2 integration tests (real QA KB) | Passing |

### What is NOT in this PR

| Feature | Step | Notes |
|---|---|---|
| SDK Skills (`.claude/*.md` + `setting_sources`) | Step 5 | Config wired, not activated |
| Streaming + persisting tool calls | Step 6b | Only final text streamed; tool calls logged |
| Workspace persistence (zip fetch/upsert) | Step 7 | Stub in `workspace.py` |
| Thinking stream to frontend | — | SDK `max_thinking_tokens` field wired; display not yet |
| Code execution artifact upload | Step 14 | Not started |
| `ANTHROPIC_API_KEY` as `SecretStr` | Pre-merge | Not yet |
| References downstream wiring (`parse_references()`) | Step 11 | Stub in `generated_files.py` |
| Full `runner.run()` integration test | Pre-merge | Unit tests cover each phase |

**Current behaviour (streaming/history):** The user sees only the final assistant message
streamed. Intermediate tool calls are not sent to the frontend and are not persisted to
the DB. Turn history for the next request is built from a single text block in the system
prompt. Step 6b will add streaming of tool-call events and structured persistence.

---

## Tests

| File | Coverage |
|---|---|
| `test_config.py` | `ClaudeAgentConfig` validation, `build_tool_policy()` |
| `test_runner.py` | `_build_options()`, `_build_system_prompt()`, history wiring, routing |
| `test_prompts.py` | All system prompt sections, reference guidelines |
| `test_history.py` | History formatting, tool message rendering, truncation |
| `test_mcp_tools.py` | `build_unique_mcp_server()`, KB tool, proxy tool, 0-indexed sources |
| `test_integration.py` | L1: streaming, KB MCP call, schema, code execution, proxy degradation. L2: real QA KB |
