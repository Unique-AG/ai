"""
Test suite for ClaudeAgentRunner.

All service dependencies are mocked — these tests are CI-safe and do not require
a real Claude API key, a running platform, or the claude-agent-sdk package.

Naming convention: test_<method>_<scenario>_<expected>
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
# Stub methods raise NotImplementedError
# ─────────────────────────────────────────────────────────────────────────────


class TestStubMethods:
    @pytest.mark.asyncio
    async def test_build_system_prompt_raises_not_implemented(self) -> None:
        """_build_system_prompt() is a Step 2b stub."""
        runner = _make_runner()
        with pytest.raises(NotImplementedError, match="Step 2b"):
            await runner._build_system_prompt()

    def test_build_history_raises_not_implemented(self) -> None:
        """_build_history() is a Step 2b stub."""
        runner = _make_runner()
        with pytest.raises(NotImplementedError, match="Step 2b"):
            runner._build_history()

    @pytest.mark.asyncio
    async def test_run_claude_loop_raises_not_implemented(self) -> None:
        """_run_claude_loop() is a Step 3 stub."""
        runner = _make_runner()
        with pytest.raises(NotImplementedError, match="Step 3"):
            await runner._run_claude_loop(prompt="hi", options={})
