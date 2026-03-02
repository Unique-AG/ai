"""
Test suite for ClaudeAgentRunner.

All service dependencies are mocked — these tests are CI-safe and do not require
a real Claude API key or a running platform. The claude-agent-sdk package is
installed (required by pyproject.toml) but query() is always mocked so no
subprocess is spawned.

Naming convention: test_<method>_<scenario>_<expected>
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeSDKError

from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.runner import ClaudeAgentRunner

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_runner(claude_config: ClaudeAgentConfig | None = None) -> ClaudeAgentRunner:
    """Construct a ClaudeAgentRunner with all services mocked."""
    mock_event = MagicMock()
    mock_event.payload.user_message.text = "hello"
    mock_event.payload.chat_id = "chat-123"
    mock_event.payload.assistant_message.id = "msg-456"

    return ClaudeAgentRunner(
        event=mock_event,
        logger=MagicMock(),
        config=MagicMock(),
        claude_config=claude_config or ClaudeAgentConfig(),
        chat_service=MagicMock(),
        content_service=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_progress_reporter=MagicMock(),
        message_step_logger=MagicMock(),
        history_manager=MagicMock(),
        debug_info_manager=MagicMock(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Runner instantiation
# ─────────────────────────────────────────────────────────────────────────────


class TestClaudeAgentRunnerInit:
    def test_runner_init_stores_all_dependencies__when_constructed_with_mocked_services(
        self,
    ) -> None:
        """All constructor args are stored as private attributes."""
        mock_event = MagicMock()
        mock_logger = MagicMock()
        mock_config = MagicMock()
        claude_config = ClaudeAgentConfig()
        mock_chat = MagicMock()
        mock_content = MagicMock()
        mock_eval = MagicMock()
        mock_post = MagicMock()
        mock_ref = MagicMock()
        mock_think = MagicMock()
        mock_progress = MagicMock()
        mock_step = MagicMock()
        mock_history = MagicMock()
        mock_debug = MagicMock()

        runner = ClaudeAgentRunner(
            event=mock_event,
            logger=mock_logger,
            config=mock_config,
            claude_config=claude_config,
            chat_service=mock_chat,
            content_service=mock_content,
            evaluation_manager=mock_eval,
            postprocessor_manager=mock_post,
            reference_manager=mock_ref,
            thinking_manager=mock_think,
            tool_progress_reporter=mock_progress,
            message_step_logger=mock_step,
            history_manager=mock_history,
            debug_info_manager=mock_debug,
        )

        assert runner._event is mock_event
        assert runner._logger is mock_logger
        assert runner._config is mock_config
        assert runner._claude_config is claude_config
        assert runner._chat_service is mock_chat
        assert runner._content_service is mock_content
        assert runner._evaluation_manager is mock_eval
        assert runner._postprocessor_manager is mock_post
        assert runner._reference_manager is mock_ref
        assert runner._thinking_manager is mock_think
        assert runner._tool_progress_reporter is mock_progress
        assert runner._message_step_logger is mock_step
        assert runner._history_manager is mock_history
        assert runner._debug_info_manager is mock_debug
        assert runner._workspace_dir is None


# ─────────────────────────────────────────────────────────────────────────────
# _build_options()
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildOptions:
    def test_build_options_default_config__produces_expected_shape(self) -> None:
        """Default ClaudeAgentConfig produces the mandatory keys with correct values."""
        runner = _make_runner()
        opts = runner._build_options(system_prompt="sys", workspace_dir=None)

        assert opts["system_prompt"] == "sys"
        assert opts["model"] == "claude-sonnet-4-20250514"
        assert opts["max_turns"] == 20
        assert opts["max_budget_usd"] == 2.0
        assert opts["permission_mode"] == "bypassPermissions"
        assert isinstance(opts["allowed_tools"], list)
        assert isinstance(opts["disallowed_tools"], list)
        assert "ANTHROPIC_API_KEY" in opts["env"]
        assert opts["include_partial_messages"] is True

    def test_build_options_with_workspace_dir__cwd_in_options(self) -> None:
        """When workspace_dir is provided, cwd appears in the options dict."""
        runner = _make_runner()
        ws = Path("/tmp/workspace/chat-123")
        opts = runner._build_options(system_prompt="sys", workspace_dir=ws)

        assert "cwd" in opts
        assert opts["cwd"] == str(ws)

    def test_build_options_without_workspace_dir__cwd_not_in_options(self) -> None:
        """When workspace_dir is None, cwd must be absent (runner is sandbox-agnostic)."""
        runner = _make_runner()
        opts = runner._build_options(system_prompt="sys", workspace_dir=None)

        assert "cwd" not in opts

    def test_build_options_code_execution_enabled__bash_write_edit_read_glob_grep_in_allowed(
        self,
    ) -> None:
        """When enable_code_execution=True, all code execution tools are in allowed_tools."""
        runner = _make_runner(ClaudeAgentConfig(enable_code_execution=True))
        opts = runner._build_options(system_prompt="sys", workspace_dir=None)

        for tool in ("Bash", "Write", "Edit", "Read", "Glob", "Grep"):
            assert tool in opts["allowed_tools"], f"{tool} must be in allowed_tools"
            assert tool not in opts["disallowed_tools"], (
                f"{tool} must not be in disallowed_tools"
            )

    def test_build_options_optional_fields__appear_in_options_when_set(self) -> None:
        """max_thinking_tokens, fallback_model, setting_sources, add_dirs, cli_path
        are only included in the options dict when explicitly set."""
        config = ClaudeAgentConfig(
            max_thinking_tokens=8192,
            fallback_model="claude-haiku-4-20250514",
            setting_sources=["project"],
            add_dirs=["/data/mounts"],
            cli_path="/usr/local/bin/claude",
        )
        runner = _make_runner(config)
        opts = runner._build_options(system_prompt="sys", workspace_dir=None)

        assert opts["max_thinking_tokens"] == 8192
        assert opts["fallback_model"] == "claude-haiku-4-20250514"
        assert opts["setting_sources"] == ["project"]
        assert opts["add_dirs"] == ["/data/mounts"]
        assert opts["cli_path"] == "/usr/local/bin/claude"

    def test_build_options_optional_fields__absent_when_not_set(self) -> None:
        """Optional fields must not appear in options when left at their None/empty default."""
        runner = _make_runner()
        opts = runner._build_options(system_prompt="sys", workspace_dir=None)

        assert "max_thinking_tokens" not in opts
        assert "fallback_model" not in opts
        assert "setting_sources" not in opts
        assert "add_dirs" not in opts
        assert "cli_path" not in opts

    def test_build_options_extra_env_merged__into_env_dict(self) -> None:
        """extra_env from ClaudeAgentConfig is merged into the env dict alongside ANTHROPIC_API_KEY."""
        config = ClaudeAgentConfig(
            extra_env={"MY_SECRET": "hunter2", "REGION": "us-east-1"}
        )
        runner = _make_runner(config)
        opts = runner._build_options(system_prompt="sys", workspace_dir=None)

        assert opts["env"]["MY_SECRET"] == "hunter2"
        assert opts["env"]["REGION"] == "us-east-1"
        assert "ANTHROPIC_API_KEY" in opts["env"]


# ─────────────────────────────────────────────────────────────────────────────
# _build_system_prompt
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildSystemPrompt:
    @pytest.mark.asyncio
    async def test_build_system_prompt_returns_override_when_set(self) -> None:
        """When system_prompt_override is non-empty it is returned verbatim."""
        config = ClaudeAgentConfig(system_prompt_override="My custom prompt")
        runner = _make_runner(config)
        runner._history_manager._loop_history = []

        result = await runner._build_system_prompt()

        assert result == "My custom prompt"

    @pytest.mark.asyncio
    async def test_build_system_prompt_composes_sections_when_no_override(self) -> None:
        """Default config with no override produces a composed prompt with key sections."""
        runner = _make_runner()
        runner._history_manager._loop_history = []
        # Ensure user_metadata returns empty (no payload metadata)
        runner._event.payload.user_metadata = None

        result = await runner._build_system_prompt()

        assert "# System" in result
        assert "# Answer Style" in result
        assert "# Reference Guidelines" in result
        assert "HtmlRendering" in result
        assert isinstance(result, str)
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_model_name(self) -> None:
        """The configured model name appears in the composed prompt."""
        config = ClaudeAgentConfig(model="claude-opus-4-20250514")
        runner = _make_runner(config)
        runner._history_manager._loop_history = []
        runner._event.payload.user_metadata = None

        result = await runner._build_system_prompt()

        assert "claude-opus-4-20250514" in result


# ─────────────────────────────────────────────────────────────────────────────
# _build_history
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildHistory:
    def test_build_history_returns_empty_list(self) -> None:
        """_build_history() returns [] — history is injected via system prompt for MVP."""
        runner = _make_runner()
        assert runner._build_history() == []


# ─────────────────────────────────────────────────────────────────────────────
# _run_claude_loop
# ─────────────────────────────────────────────────────────────────────────────


async def _mock_query_gen(*messages):
    """Async generator that yields each provided mock message."""
    for msg in messages:
        yield msg


async def _raising_gen(exc: Exception):
    """Async generator that raises exc on first iteration."""
    raise exc
    yield  # pragma: no cover — makes this a generator


class TestRunClaudeLoop:
    @pytest.mark.asyncio
    async def test_run_claude_loop_streams_text_deltas_to_chat_service(self) -> None:
        """Each text_delta calls modify_assistant_message_async with growing text."""
        runner = _make_runner()
        runner._chat_service.modify_assistant_message_async = AsyncMock()

        delta1 = MagicMock()
        delta1.type = "content_block_delta"
        delta1.delta = MagicMock()
        delta1.delta.type = "text_delta"
        delta1.delta.text = "Hello"

        delta2 = MagicMock()
        delta2.type = "content_block_delta"
        delta2.delta = MagicMock()
        delta2.delta.type = "text_delta"
        delta2.delta.text = " world"

        with patch("unique_toolkit.agentic.claude_agent.runner.query") as mock_query:
            mock_query.return_value = _mock_query_gen(delta1, delta2)
            await runner._run_claude_loop(prompt="hi", options={})

        calls = runner._chat_service.modify_assistant_message_async.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["content"] == "Hello"
        assert calls[1].kwargs["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_run_claude_loop_returns_accumulated_text(self) -> None:
        """Return value is the full concatenated text from all text_deltas."""
        runner = _make_runner()
        runner._chat_service.modify_assistant_message_async = AsyncMock()

        delta1 = MagicMock()
        delta1.type = "content_block_delta"
        delta1.delta = MagicMock()
        delta1.delta.type = "text_delta"
        delta1.delta.text = "Hello"

        delta2 = MagicMock()
        delta2.type = "content_block_delta"
        delta2.delta = MagicMock()
        delta2.delta.type = "text_delta"
        delta2.delta.text = " world"

        with patch("unique_toolkit.agentic.claude_agent.runner.query") as mock_query:
            mock_query.return_value = _mock_query_gen(delta1, delta2)
            result = await runner._run_claude_loop(prompt="hi", options={})

        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_run_claude_loop_handles_result_message_when_no_text_accumulated(
        self,
    ) -> None:
        """When no text_deltas were received, result.result is used as accumulated text."""
        runner = _make_runner()
        runner._chat_service.modify_assistant_message_async = AsyncMock()

        result_msg = MagicMock()
        result_msg.type = "result"
        result_msg.result = "Final answer text"

        with patch("unique_toolkit.agentic.claude_agent.runner.query") as mock_query:
            mock_query.return_value = _mock_query_gen(result_msg)
            result = await runner._run_claude_loop(prompt="hi", options={})

        assert result == "Final answer text"

    @pytest.mark.asyncio
    async def test_run_claude_loop_logs_tool_use_blocks(self) -> None:
        """tool_use blocks in AssistantMessage content trigger debug log with tool name."""
        runner = _make_runner()
        runner._chat_service.modify_assistant_message_async = AsyncMock()

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "mcp__unique_platform__search_knowledge_base"
        tool_block.input = {"search_query": "interest rates"}

        assistant_msg = MagicMock(spec=AssistantMessage)
        assistant_msg.type = "assistant"
        assistant_msg.content = [tool_block]

        with patch("unique_toolkit.agentic.claude_agent.runner.query") as mock_query:
            mock_query.return_value = _mock_query_gen(assistant_msg)
            await runner._run_claude_loop(prompt="hi", options={})

        debug_calls = [str(c) for c in runner._logger.debug.call_args_list]
        assert any(
            "mcp__unique_platform__search_knowledge_base" in c for c in debug_calls
        )

    @pytest.mark.asyncio
    async def test_run_claude_loop_catches_sdk_error_gracefully(self) -> None:
        """ClaudeSDKError does not propagate; returns a user-facing error string."""
        runner = _make_runner()
        runner._chat_service.modify_assistant_message_async = AsyncMock()

        with patch("unique_toolkit.agentic.claude_agent.runner.query") as mock_query:
            mock_query.return_value = _raising_gen(ClaudeSDKError("sdk exploded"))
            result = await runner._run_claude_loop(prompt="hi", options={})

        assert "error" in result.lower()
        runner._logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_run_claude_loop_catches_generic_exception_gracefully(self) -> None:
        """Unexpected exceptions do not propagate; returns a user-facing error string."""
        runner = _make_runner()
        runner._chat_service.modify_assistant_message_async = AsyncMock()

        with patch("unique_toolkit.agentic.claude_agent.runner.query") as mock_query:
            mock_query.return_value = _raising_gen(RuntimeError("boom"))
            result = await runner._run_claude_loop(prompt="hi", options={})

        assert "error" in result.lower()
        runner._logger.error.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# _run_post_processing
# ─────────────────────────────────────────────────────────────────────────────


class TestRunPostProcessing:
    @pytest.mark.asyncio
    async def test_run_post_processing_calls_eval_and_postprocessor_concurrently(
        self,
    ) -> None:
        """Both managers are called when claude_result is non-empty."""
        runner = _make_runner()
        runner._evaluation_manager.run_evaluations = AsyncMock(return_value=[])
        runner._postprocessor_manager.run_postprocessors = AsyncMock(return_value=None)

        await runner._run_post_processing("Some final answer text")

        runner._evaluation_manager.run_evaluations.assert_called_once()
        runner._postprocessor_manager.run_postprocessors.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_post_processing_skips_when_result_empty(self) -> None:
        """Neither manager is called when claude_result is an empty string."""
        runner = _make_runner()
        runner._evaluation_manager.run_evaluations = AsyncMock(return_value=[])
        runner._postprocessor_manager.run_postprocessors = AsyncMock(return_value=None)

        await runner._run_post_processing("")

        runner._evaluation_manager.run_evaluations.assert_not_called()
        runner._postprocessor_manager.run_postprocessors.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# _format_history (public API usage)
# ─────────────────────────────────────────────────────────────────────────────


class TestFormatHistory:
    def test_format_history_uses_public_get_loop_history(self) -> None:
        """_format_history() calls get_loop_history(), not ._loop_history directly."""
        runner = _make_runner()
        runner._history_manager.get_loop_history = MagicMock(return_value=[])

        runner._format_history()

        runner._history_manager.get_loop_history.assert_called_once()
