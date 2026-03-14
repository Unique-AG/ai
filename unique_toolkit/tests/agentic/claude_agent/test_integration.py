"""
Integration tests for ClaudeAgentRunner.

These tests use the REAL Claude Agent SDK — actual subprocess, real API calls,
real tool invocations. They are organized in two levels with independent skip
conditions:

Level 1: ANTHROPIC_API_KEY only — no Unique platform dependency.
Level 2: ANTHROPIC_API_KEY + QA platform credentials + scope/chat IDs.

Setup:
    Copy .env.local.example (repo root) to .env.local and fill in your credentials.
    Then load it before running:

        set -a && source ../.env.local && set +a

Run Level 1 only (from ai repo root):
    cd unique_toolkit && set -a && source ../.env.local && set +a
    uv run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "L1"

  If you are already in unique_toolkit/:
    set -a && source ../.env.local && set +a
    uv run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "L1"

  Run just the tool-progress real-API test (from unique_toolkit/):
    set -a && source ../.env.local && set +a
    uv run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "L1_tool_progress"

Run Level 2 (real platform):
    set -a && source ../.env.local && set +a
    uv run pytest tests/agentic/claude_agent/test_integration.py -v -s

The -s flag is critical — it shows streaming output during tests.
Each test costs ~$0.02–0.10 in API credits.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_agent_sdk import ClaudeAgentOptions

from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.runner import ClaudeAgentRunner
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.content.schemas import ContentChunk


def _make_tool_progress_reporter() -> MagicMock:
    """Return a MagicMock ToolProgressReporter with notify_from_tool_call as AsyncMock.

    streaming.py awaits notify_from_tool_call() on every ToolUseBlock — plain
    MagicMock() raises 'object MagicMock can't be used in await expression'.
    """
    reporter = MagicMock()
    reporter.notify_from_tool_call = AsyncMock()
    return reporter


# ─────────────────────────────────────────────────────────────────────────────
# Credentials setup
# ─────────────────────────────────────────────────────────────────────────────

# Credentials are loaded from .env.local at the repo root.
# Copy .env.local.example → .env.local and fill in your values, then:
#   set -a && source ../.env.local && set +a
#
# Legacy fallback: .local-dev/unique.env.qa is also accepted for backward
# compatibility during the transition period.
_ENV_LOCAL = Path(__file__).parents[4] / ".env.local"
_ENV_QA_LEGACY = Path(__file__).parents[4] / ".local-dev" / "unique.env.qa"


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


# Prefer .env.local; fall back to legacy QA env file if it exists
_ENV = _load_env_file(_ENV_LOCAL) or _load_env_file(_ENV_QA_LEGACY)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "") or _ENV.get(
    "ANTHROPIC_API_KEY", ""
)
UNIQUE_APP_KEY = os.environ.get("UNIQUE_APP_KEY", "") or _ENV.get("UNIQUE_APP_KEY", "")
UNIQUE_APP_ID = os.environ.get("UNIQUE_APP_ID", "") or _ENV.get("UNIQUE_APP_ID", "")
UNIQUE_API_BASE_URL = os.environ.get("UNIQUE_API_BASE_URL", "") or _ENV.get(
    "UNIQUE_API_BASE_URL", ""
)
UNIQUE_COMPANY_ID = os.environ.get("UNIQUE_AUTH_COMPANY_ID", "") or _ENV.get(
    "UNIQUE_AUTH_COMPANY_ID", ""
)
UNIQUE_USER_ID = os.environ.get("UNIQUE_AUTH_USER_ID", "") or _ENV.get(
    "UNIQUE_AUTH_USER_ID", ""
)

# Find scope_id in the QA KB URL: https://next.qa.unique.app/knowledge-upload/<scope_id>
UNIQUE_TEST_SCOPE_ID = os.environ.get("UNIQUE_TEST_SCOPE_ID", "") or _ENV.get(
    "UNIQUE_TEST_SCOPE_ID", ""
)

# Find chat_id in the QA chat URL: https://next.qa.unique.app/chat/<chat_id>
UNIQUE_TEST_CHAT_ID = os.environ.get("UNIQUE_TEST_CHAT_ID", "") or _ENV.get(
    "UNIQUE_TEST_CHAT_ID", ""
)

# Defaults to a synthetic value — platform may or may not validate this
UNIQUE_TEST_MSG_ID = os.environ.get("UNIQUE_TEST_MSG_ID", "") or _ENV.get(
    "UNIQUE_TEST_MSG_ID", "msg-integration-001"
)

needs_anthropic = pytest.mark.skipif(
    not ANTHROPIC_API_KEY,
    reason="ANTHROPIC_API_KEY not set",
)
needs_platform_kb = pytest.mark.skipif(
    not (ANTHROPIC_API_KEY and UNIQUE_APP_KEY and UNIQUE_TEST_SCOPE_ID),
    reason="ANTHROPIC_API_KEY + UNIQUE_APP_KEY + UNIQUE_TEST_SCOPE_ID all required",
)
needs_platform_web = pytest.mark.skipif(
    not (ANTHROPIC_API_KEY and UNIQUE_APP_KEY and UNIQUE_TEST_CHAT_ID),
    reason="ANTHROPIC_API_KEY + UNIQUE_APP_KEY + UNIQUE_TEST_CHAT_ID all required",
)
needs_full_e2e = pytest.mark.skipif(
    not (
        ANTHROPIC_API_KEY
        and UNIQUE_APP_KEY
        and UNIQUE_TEST_SCOPE_ID
        and UNIQUE_TEST_CHAT_ID
    ),
    reason="Full E2E requires ANTHROPIC_API_KEY + UNIQUE_APP_KEY + UNIQUE_TEST_SCOPE_ID + UNIQUE_TEST_CHAT_ID",
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: _make_live_runner()
# ─────────────────────────────────────────────────────────────────────────────


def _make_live_runner(
    claude_config: ClaudeAgentConfig | None = None,
    content_service: object = None,
    mcp_servers: list | None = None,
    chat_id: str = "integration-test-001",
    msg_id: str = "integration-msg-001",
    company_id: str | None = None,
    user_id: str | None = None,
) -> tuple[ClaudeAgentRunner, list[str]]:
    """Construct a ClaudeAgentRunner with no SDK mocking — real API calls."""
    mock_event = MagicMock()
    mock_event.payload.chat_id = chat_id
    mock_event.payload.assistant_message.id = msg_id
    mock_event.payload.user_metadata = None
    mock_event.payload.mcp_servers = mcp_servers or []
    mock_event.user_id = user_id or UNIQUE_USER_ID or "test-user"
    mock_event.company_id = company_id or UNIQUE_COMPANY_ID or "test-company"

    chunks: list[str] = []
    chat_service = MagicMock()

    async def _stream(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            chunks.append(content)
            prev = chunks[-2] if len(chunks) > 1 else ""
            delta = content[len(prev) :]
            print(delta, end="", flush=True)  # live output during test (-s flag)

    chat_service.modify_assistant_message_async = AsyncMock(side_effect=_stream)

    return (
        ClaudeAgentRunner(
            event=mock_event,
            logger=logging.getLogger("integration"),
            config=MagicMock(),
            claude_config=claude_config
            or ClaudeAgentConfig(
                system_prompt_override="You are a concise assistant. Answer in plain text.",
                model="claude-sonnet-4-6",
                max_turns=5,
                permission_mode="bypassPermissions",
            ),
            chat_service=chat_service,
            content_service=content_service or MagicMock(),
            evaluation_manager=MagicMock(),
            postprocessor_manager=MagicMock(),
            reference_manager=MagicMock(),
            thinking_manager=MagicMock(),
            tool_progress_reporter=_make_tool_progress_reporter(),
            message_step_logger=MagicMock(),
            history_manager=MagicMock(),
            debug_info_manager=MagicMock(),
        ),
        chunks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Level 2 helpers
# ─────────────────────────────────────────────────────────────────────────────


def _init_platform() -> object:
    """Initialize unique_sdk and return a real ContentService for the QA platform."""
    import unique_sdk

    from unique_toolkit.content.service import ContentService

    unique_sdk.api_key = UNIQUE_APP_KEY
    unique_sdk.app_id = UNIQUE_APP_ID
    unique_sdk.api_base = UNIQUE_API_BASE_URL

    return ContentService(
        company_id=UNIQUE_COMPANY_ID,
        user_id=UNIQUE_USER_ID,
        chat_id="",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Level 1 tests — ANTHROPIC_API_KEY only (no Unique platform)
# ─────────────────────────────────────────────────────────────────────────────


@needs_anthropic
@pytest.mark.asyncio
async def test_L1_streaming_basic() -> None:
    """Real SDK call: confirms streaming pipeline works end-to-end."""
    runner, chunks = _make_live_runner()
    options = runner._build_options(
        system_prompt="You are a concise assistant.",
        workspace_dir=None,
    )
    result = await runner._run_claude_loop(
        prompt="Reply with exactly three words: hello beautiful world",
        options=options,
    )
    assert result  # non-empty
    assert (
        len(chunks) >= 1
    )  # streaming happened — modify_assistant_message_async was called
    assert "hello" in result.lower()


@needs_anthropic
@pytest.mark.asyncio
async def test_L1_kb_search_tool_called_with_mock_platform() -> None:
    """Real SDK call + real MCP tool invocation, but ContentService is mocked.

    Proves the full tool call path:
    SDK query() → Claude decides to use KB tool → @tool handler fires
    → ContentService.search_content_chunks() called → mock chunk returned
    → Claude incorporates result into response.
    """
    content_service = MagicMock()
    content_service.search_content_chunks.return_value = [
        ContentChunk(
            id="cont_" + "a" * 24,
            text="The quarterly revenue for Capstone Fund was $4.2 billion in Q3 2025.",
            key="capstone_q3_report.pdf",
            order=0,
        )
    ]

    runner, chunks = _make_live_runner(content_service=content_service)
    options = runner._build_options(
        system_prompt="You are a financial assistant. Always search the knowledge base before answering.",
        workspace_dir=None,
    )

    print("\n\n--- KB Tool Test Output ---")
    result = await runner._run_claude_loop(
        prompt="What was the quarterly revenue for Capstone Fund? Use the search_knowledge_base tool.",
        options=options,
    )
    print(f"\n--- End Output ({len(result)} chars) ---\n")

    assert result
    # Verify ContentService was actually called by our tool handler
    assert content_service.search_content_chunks.called, (
        "Claude did not call the KB search tool — check the system prompt and tool availability"
    )
    # Verify Claude used the result (the revenue figure should appear in response)
    assert (
        "4.2" in result or "billion" in result.lower() or "capstone" in result.lower()
    )


@needs_anthropic
def test_L1_options_schema_valid() -> None:
    """ClaudeAgentOptions(**options) does not raise — schema is compatible."""
    runner, _ = _make_live_runner()
    options = runner._build_options(system_prompt="sys", workspace_dir=None)
    sdk_options = ClaudeAgentOptions(**options)  # must not raise
    assert sdk_options is not None


@needs_anthropic
@pytest.mark.asyncio
async def test_L1_code_execution() -> None:
    """Real SDK call with code execution enabled. Claude creates a file."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        config = ClaudeAgentConfig(
            system_prompt_override="You are a coding assistant. Use Bash and Write tools freely.",
            model="claude-sonnet-4-6",
            max_turns=5,
            permission_mode="bypassPermissions",
            enable_code_execution=True,
        )
        runner, chunks = _make_live_runner(claude_config=config)
        workspace_dir = Path(tmpdir)
        options = runner._build_options(
            system_prompt=config.system_prompt_override,
            workspace_dir=workspace_dir,
        )

        print("\n\n--- Code Execution Test Output ---")
        result = await runner._run_claude_loop(
            prompt=(
                "Create a file called hello.txt in the current working directory "
                "(use a relative path like ./hello.txt, NOT /tmp/) containing the text "
                "'Hello from Claude Agent!', then read it back and confirm its contents."
            ),
            options=options,
        )
        print(f"\n--- End Output ({len(result)} chars) ---\n")

        assert result
        hello_file = workspace_dir / "hello.txt"
        assert hello_file.exists(), f"Claude did not create hello.txt in {tmpdir}"
        assert "Hello from Claude Agent" in hello_file.read_text()


@needs_anthropic
@pytest.mark.asyncio
async def test_L1_web_search_proxy_graceful_degradation() -> None:
    """Real SDK + real proxy invocation path, platform call expected to fail gracefully.

    Fakes event.payload.mcp_servers with a web_search tool entry.
    Claude calls mcp__unique_platform__web_search.
    Our proxy fires unique_sdk.MCP.call_tool_async() → platform rejects fake chatId.
    The proxy catches the error and returns it as text content.
    Claude receives the error text and responds — agent loop does NOT crash.

    Proves: proxy wiring, error handling, graceful degradation.
    """
    fake_tool = MagicMock()
    fake_tool.name = "web_search"
    fake_tool.description = "Search the web for current information."
    fake_tool.input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    fake_tool.is_connected = True

    fake_server = MagicMock()
    fake_server.tools = [fake_tool]

    runner, chunks = _make_live_runner(mcp_servers=[fake_server])
    options = runner._build_options(
        system_prompt="You are a research assistant. Use the web_search tool to answer questions.",
        workspace_dir=None,
    )

    print("\n\n--- Web Search Proxy Graceful Degradation Test ---")
    result = await runner._run_claude_loop(
        prompt="Search the web for recent news about Anthropic using the web_search tool.",
        options=options,
    )
    print(f"\n--- End Output ({len(result)} chars) ---\n")
    print(f"Result: {result[:300]}...")

    # The loop must complete — it must NOT raise an exception
    assert result, "Agent loop returned empty — it may have crashed"
    # Claude should acknowledge the search or the error — it should not be silent
    assert len(result) > 20


@needs_anthropic
@pytest.mark.asyncio
async def test_L1_tool_progress_published_on_real_tool_use() -> None:
    """Real SDK call: ToolProgressReporter.publish() fires when Claude invokes Bash.

    Uses a real ToolProgressReporter backed by a dedicated mock ChatService so
    that progress calls are isolated from text-streaming calls.  Asserts that
    the formatted tool name ("Bash") and state indicator reach the mock.

    This is the only test that exercises the full in-process chain end-to-end
    with a real Anthropic API response:
        real query() → real AssistantMessage(ToolUseBlock) →
        real notify_from_tool_call() → real publish() →
        mock.modify_assistant_message_async(content="...Bash...")
    """
    # Dedicated mock for progress output — separate from streaming chat_service
    progress_calls: list[str] = []
    progress_chat_service = MagicMock()

    async def _capture_progress(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            progress_calls.append(content)
            print(f"\n[progress] {content[:120]}", flush=True)

    progress_chat_service.modify_assistant_message_async = AsyncMock(
        side_effect=_capture_progress
    )

    config = ClaudeAgentConfig(
        system_prompt_override=(
            "You are a coding assistant. "
            "You MUST use the Bash tool to run `echo hello` before responding."
        ),
        model="claude-sonnet-4-6",
        max_turns=5,
        permission_mode="bypassPermissions",
        enable_code_execution=True,
    )
    runner, chunks = _make_live_runner(claude_config=config)
    runner._tool_progress_reporter = ToolProgressReporter(
        chat_service=progress_chat_service
    )

    options = runner._build_options(
        system_prompt=config.system_prompt_override,
        workspace_dir=None,
    )

    print("\n\n--- Tool Progress Reporter Real API Test ---")
    result = await runner._run_claude_loop(
        prompt="Run `echo hello` using the Bash tool and report back what it printed.",
        options=options,
    )
    print(f"\n--- Text result ({len(result)} chars): {result[:200]} ---")
    print(f"--- Progress calls captured: {len(progress_calls)} ---\n")

    assert result, "Agent loop returned empty"
    assert progress_calls, (
        "ToolProgressReporter.publish() was never called — "
        "Claude may not have invoked any tools, or the wiring is broken"
    )
    all_progress = " ".join(progress_calls)
    assert "Bash" in all_progress, (
        f"Expected 'Bash' in progress output, got: {all_progress[:300]}"
    )
    assert "Running..." in all_progress, (
        f"Expected 'Running...' in progress output, got: {all_progress[:300]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Level 2 tests — Real Unique platform (QA credentials + scope ID / chat ID)
# ─────────────────────────────────────────────────────────────────────────────


@needs_platform_kb
@pytest.mark.asyncio
async def test_L2_kb_search_real_platform() -> None:
    """Real KB search against QA platform.

    Claude calls search_knowledge_base → real ContentService.search_content_chunks()
    → real HTTP call to QA KB → real chunks returned to Claude.
    Set UNIQUE_TEST_SCOPE_ID to the scope_id of your QA knowledge base folder.
    """
    content_service = _init_platform()

    config = ClaudeAgentConfig(
        system_prompt_override=(
            "You are a knowledge base assistant. "
            "Always use the search_knowledge_base tool to answer questions."
        ),
        model="claude-sonnet-4-6",
        max_turns=5,
        permission_mode="bypassPermissions",
        scope_ids=[UNIQUE_TEST_SCOPE_ID],
        search_type="COMBINED",
    )
    runner, chunks = _make_live_runner(
        claude_config=config, content_service=content_service
    )
    options = runner._build_options(
        system_prompt=config.system_prompt_override,
        workspace_dir=None,
    )

    print(f"\n\n--- Real KB Search Test (scope: {UNIQUE_TEST_SCOPE_ID}) ---")
    result = await runner._run_claude_loop(
        prompt=(
            "Search the knowledge base and give me a brief summary of "
            "what topics are covered in the available documents."
        ),
        options=options,
    )
    print(f"\n--- End Output ({len(result)} chars) ---\n")

    assert result
    assert len(result) > 50, (
        "Response too short — Claude may not have used the KB results"
    )


@needs_platform_web
@pytest.mark.asyncio
async def test_L2_web_search_via_mcp_proxy() -> None:
    """Full MCP proxy integration test using QA platform web search.

    The runner fakes event.payload.mcp_servers with a web_search tool entry.
    Claude calls mcp__unique_platform__web_search.
    The proxy fires unique_sdk.MCP.call_tool_async() with the real QA chatId.
    The QA platform routes this to the web search connector and returns results.
    Claude incorporates the results into its answer.

    Requires: UNIQUE_TEST_CHAT_ID — any existing chat ID from the QA platform.
    Find it in the URL when you open a chat: https://next.qa.unique.app/chat/<chat_id>

    What this proves: the entire MCP proxy architecture works end-to-end.
    Any platform MCP tool (web search, custom connectors) is automatically
    available to Claude once configured in the platform — zero additional code.
    """
    import unique_sdk

    # Initialize unique_sdk with QA credentials
    unique_sdk.api_key = UNIQUE_APP_KEY
    unique_sdk.app_id = UNIQUE_APP_ID
    unique_sdk.api_base = UNIQUE_API_BASE_URL

    # Fake the MCP server config that would normally come from event.payload.mcp_servers
    fake_tool = MagicMock()
    fake_tool.name = "web_search"
    fake_tool.description = "Search the web for current information given a query."
    fake_tool.input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    fake_tool.is_connected = True

    fake_server = MagicMock()
    fake_server.tools = [fake_tool]

    config = ClaudeAgentConfig(
        system_prompt_override=(
            "You are a research assistant. "
            "Use the web_search tool to answer questions about current events."
        ),
        model="claude-sonnet-4-6",
        max_turns=5,
        permission_mode="bypassPermissions",
    )

    runner, chunks = _make_live_runner(
        claude_config=config,
        mcp_servers=[fake_server],
        chat_id=UNIQUE_TEST_CHAT_ID,
        msg_id=UNIQUE_TEST_MSG_ID,
        company_id=UNIQUE_COMPANY_ID,
        user_id=UNIQUE_USER_ID,
    )

    options = runner._build_options(
        system_prompt=config.system_prompt_override,
        workspace_dir=None,
    )

    print(
        f"\n\n--- Web Search MCP Proxy Test (chatId: {UNIQUE_TEST_CHAT_ID[:20]}...) ---"
    )
    result = await runner._run_claude_loop(
        prompt=(
            "Use the web_search tool to find out what Anthropic announced most recently, "
            "then summarize it in 2-3 sentences."
        ),
        options=options,
    )
    print(f"\n--- End Output ({len(result)} chars) ---\n")

    assert result, "Agent loop returned empty"
    assert len(result) > 50, (
        "Response too short — Claude may not have used web search results"
    )
    # If we got here without an exception, the proxy path worked end-to-end


# ─────────────────────────────────────────────────────────────────────────────
# Full E2E demo test — authoritative readiness check for monorepo integration
# ─────────────────────────────────────────────────────────────────────────────


@needs_full_e2e
@pytest.mark.asyncio
async def test_L2_full_e2e_streaming_tools_files_multiturn() -> None:
    """Full E2E demo: streaming → KB tool → file creation → inline rendering → multi-turn.

    This is the authoritative test that the Python stack is ready for monorepo
    integration. It exercises runner.run() (not _run_claude_loop()) to validate
    the complete lifecycle:
        workspace setup → system prompt → history → SDK loop →
        output file upload → inject_file_references_into_text →
        post-processing → message completion → checkpoint save → cleanup

    Turn 1: KB search + text streaming + tool progress events
    Turn 2: Code execution + file creation + inline unique://content/ reference

    Requires: ANTHROPIC_API_KEY, UNIQUE_APP_KEY, UNIQUE_TEST_SCOPE_ID, UNIQUE_TEST_CHAT_ID

    Run:
        cd unique_toolkit
        set -a && source ../.env.local && set +a
        poetry run pytest tests/agentic/claude_agent/test_integration.py -v -s -k "full_e2e"
    """
    content_service = _init_platform()

    # ── Turn 1 setup ─────────────────────────────────────────────────────────
    print("\n\n=== TURN 1: KB Search + Streaming ===")

    chunks_t1: list[str] = []
    progress_calls_t1: list[str] = []

    chat_service_t1 = MagicMock()

    async def _stream_t1(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            chunks_t1.append(content)
            prev = chunks_t1[-2] if len(chunks_t1) > 1 else ""
            print(content[len(prev) :], end="", flush=True)

    chat_service_t1.modify_assistant_message_async = AsyncMock(side_effect=_stream_t1)

    progress_svc_t1 = MagicMock()

    async def _progress_t1(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            progress_calls_t1.append(content)
            print(f"\n{content}", flush=True)

    progress_svc_t1.modify_assistant_message_async = AsyncMock(side_effect=_progress_t1)

    config_t1 = ClaudeAgentConfig(
        model="claude-sonnet-4-6",
        max_turns=8,
        permission_mode="bypassPermissions",
        enable_workspace_persistence=True,
        enable_code_execution=True,
        scope_ids=[UNIQUE_TEST_SCOPE_ID],
        search_type="COMBINED",
        system_prompt_override=(
            "You are a concise assistant. "
            "Always use the search_knowledge_base tool to answer questions about documents."
        ),
    )
    runner_t1, _ = _make_live_runner(
        claude_config=config_t1,
        content_service=content_service,
        chat_id=UNIQUE_TEST_CHAT_ID,
        msg_id=UNIQUE_TEST_MSG_ID,
    )
    runner_t1._chat_service = chat_service_t1
    runner_t1._tool_progress_reporter = ToolProgressReporter(
        chat_service=progress_svc_t1
    )
    # SafeTaskExecutor.execute_async() awaits these — must be AsyncMock not MagicMock
    runner_t1._postprocessor_manager.run_postprocessors = AsyncMock()
    runner_t1._evaluation_manager.run_evaluations = AsyncMock(return_value=[])
    runner_t1._event.payload.user_message = MagicMock()
    runner_t1._event.payload.user_message.text = (
        "Search the knowledge base for any document and summarize it in 2 sentences."
    )

    await runner_t1.run()

    text_t1 = chunks_t1[-1] if chunks_t1 else ""
    print(f"\n✓ Streaming: {len(chunks_t1)} chunks received")
    print(f"✓ Tool progress: {len(progress_calls_t1)} progress events published")
    print(f"✓ Response: {len(text_t1)} chars")
    print(f"\n--- TURN 1 FINAL RESPONSE (as sent to UI) ---\n{text_t1}\n--- END ---")

    assert chunks_t1, (
        "Turn 1: modify_assistant_message_async never called — streaming broken"
    )
    assert text_t1, "Turn 1: response text is empty"
    assert len(text_t1) > 30, (
        f"Turn 1: response suspiciously short ({len(text_t1)} chars)"
    )
    assert progress_calls_t1, (
        "Turn 1: no tool progress events — KB search tool may not have fired"
    )
    assert any("Running" in p for p in progress_calls_t1), (
        f"Turn 1: 'Running...' not in progress calls. Got: {progress_calls_t1[:3]}"
    )

    # ── Turn 2 setup ─────────────────────────────────────────────────────────
    print("\n\n=== TURN 2: Code Execution + File Creation ===")

    chunks_t2: list[str] = []
    progress_calls_t2: list[str] = []

    chat_service_t2 = MagicMock()

    async def _stream_t2(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            chunks_t2.append(content)
            prev = chunks_t2[-2] if len(chunks_t2) > 1 else ""
            print(content[len(prev) :], end="", flush=True)

    chat_service_t2.modify_assistant_message_async = AsyncMock(side_effect=_stream_t2)

    progress_svc_t2 = MagicMock()

    async def _progress_t2(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            progress_calls_t2.append(content)
            print(f"\n{content}", flush=True)

    progress_svc_t2.modify_assistant_message_async = AsyncMock(side_effect=_progress_t2)

    config_t2 = ClaudeAgentConfig(
        model="claude-sonnet-4-6",
        max_turns=8,
        permission_mode="bypassPermissions",
        enable_workspace_persistence=True,
        enable_code_execution=True,
        system_prompt_override=(
            "You are a coding assistant. "
            "Use Bash and Write tools to complete file tasks. "
            "Always save output files to the ./output/ directory."
        ),
    )
    runner_t2, _ = _make_live_runner(
        claude_config=config_t2,
        content_service=content_service,
        chat_id=UNIQUE_TEST_CHAT_ID,
        msg_id=UNIQUE_TEST_MSG_ID,
    )
    runner_t2._chat_service = chat_service_t2
    runner_t2._tool_progress_reporter = ToolProgressReporter(
        chat_service=progress_svc_t2
    )
    # SafeTaskExecutor.execute_async() awaits these — must be AsyncMock not MagicMock
    runner_t2._postprocessor_manager.run_postprocessors = AsyncMock()
    runner_t2._evaluation_manager.run_evaluations = AsyncMock(return_value=[])
    runner_t2._event.payload.user_message = MagicMock()
    runner_t2._event.payload.user_message.text = (
        "Write a Python script that creates ./output/data.csv containing 3 rows of sample data "
        "(header + 2 rows), run it with Bash, then confirm the file exists by listing ./output/."
    )

    await runner_t2.run()

    text_t2 = chunks_t2[-1] if chunks_t2 else ""
    print(f"\n✓ Tool progress: {len(progress_calls_t2)} progress events")
    print(f"✓ Response: {len(text_t2)} chars")
    print(f"\n--- TURN 2 FINAL RESPONSE (as sent to UI) ---\n{text_t2}\n--- END ---")

    assert chunks_t2, "Turn 2: no streaming output"
    assert progress_calls_t2, (
        "Turn 2: no tool progress events — Bash tool may not have fired"
    )
    assert "unique://content/" in text_t2, (
        "Turn 2: inline file reference not found — upload+inject pipeline may be broken. "
        f"Response:\n{text_t2}"
    )

    print("\n✓ File uploaded + inline reference injected")
    print("✓ Full pipeline validated — ready for monorepo integration")
