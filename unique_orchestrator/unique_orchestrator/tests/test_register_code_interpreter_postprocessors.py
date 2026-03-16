"""
Tests for _register_code_interpreter_postprocessors.

Covers the changed lines in unique_ai_builder.py that simplified the code
interpreter setup:  the helper now only sources config from the tools list
(never from the removed `responses_api_config.code_interpreter` field) and
always registers both postprocessors when a matching enabled tool is found.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessor,
)
from unique_toolkit.agentic.tools.tool import ToolBuildConfig

from unique_orchestrator.unique_ai_builder import (
    _register_code_interpreter_postprocessors,
)


def _make_code_interpreter_tool(
    *,
    is_enabled: bool = True,
    config: CodeInterpreterExtendedConfig | None = None,
) -> ToolBuildConfig:
    return ToolBuildConfig(
        name=OpenAIBuiltInToolName.CODE_INTERPRETER,
        configuration=config or CodeInterpreterExtendedConfig(),
        is_enabled=is_enabled,
    )


def _make_other_tool() -> MagicMock:
    """Return a mock that looks like an enabled tool with a non-CODE_INTERPRETER name."""
    tool = MagicMock(spec=ToolBuildConfig)
    tool.is_enabled = True
    tool.name = "some_other_tool"
    return tool


def _make_postprocessor_manager() -> MagicMock:
    mgr = MagicMock()
    mgr._postprocessors = []
    mgr.add_postprocessor.side_effect = lambda p: mgr._postprocessors.append(p)
    return mgr


# ---------------------------------------------------------------------------
# No postprocessors registered
# ---------------------------------------------------------------------------


class TestNoPostprocessorsRegistered:
    @pytest.mark.ai
    def test_empty_tools_list_registers_no_postprocessors(self):
        """Empty tools list: add_postprocessor must never be called."""
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        mgr.add_postprocessor.assert_not_called()

    @pytest.mark.ai
    def test_disabled_code_interpreter_tool_registers_no_postprocessors(self):
        """A CODE_INTERPRETER tool with is_enabled=False must be skipped."""
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[_make_code_interpreter_tool(is_enabled=False)],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        mgr.add_postprocessor.assert_not_called()

    @pytest.mark.ai
    def test_non_code_interpreter_enabled_tool_registers_no_postprocessors(self):
        """An enabled tool that is NOT CODE_INTERPRETER must not trigger registration."""
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[_make_other_tool()],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        mgr.add_postprocessor.assert_not_called()


# ---------------------------------------------------------------------------
# Postprocessor types registered when tool is enabled
# ---------------------------------------------------------------------------


class TestPostprocessorTypesRegistered:
    @pytest.mark.ai
    def test_registers_exactly_two_postprocessors(self):
        """One enabled CODE_INTERPRETER tool must cause exactly two add_postprocessor calls."""
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[_make_code_interpreter_tool()],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        assert mgr.add_postprocessor.call_count == 2

    @pytest.mark.ai
    def test_first_postprocessor_is_show_executed_code(self):
        """The first registered postprocessor must be a ShowExecutedCodePostprocessor."""
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[_make_code_interpreter_tool()],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        first_call_arg = mgr.add_postprocessor.call_args_list[0][0][0]
        assert isinstance(first_call_arg, ShowExecutedCodePostprocessor)

    @pytest.mark.ai
    def test_second_postprocessor_is_display_files(self):
        """The second registered postprocessor must be a DisplayCodeInterpreterFilesPostProcessor."""
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[_make_code_interpreter_tool()],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        second_call_arg = mgr.add_postprocessor.call_args_list[1][0][0]
        assert isinstance(second_call_arg, DisplayCodeInterpreterFilesPostProcessor)


# ---------------------------------------------------------------------------
# Config values are threaded through correctly
# ---------------------------------------------------------------------------


class TestConfigPassthrough:
    @pytest.mark.ai
    def test_show_executed_code_postprocessor_receives_tool_config(self):
        """ShowExecutedCodePostprocessor must be initialised with the config from the tool."""
        from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
            ShowExecutedCodePostprocessorConfig,
        )

        custom_code_display_config = ShowExecutedCodePostprocessorConfig(
            sleep_time_before_display=1.5
        )
        ci_config = CodeInterpreterExtendedConfig(
            executed_code_display_config=custom_code_display_config
        )
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[_make_code_interpreter_tool(config=ci_config)],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        postprocessor: ShowExecutedCodePostprocessor = mgr.add_postprocessor.call_args_list[0][0][0]
        assert postprocessor._config is custom_code_display_config

    @pytest.mark.ai
    def test_display_files_postprocessor_receives_client_and_company_id(self):
        """DisplayCodeInterpreterFilesPostProcessor must receive the client and company_id."""
        mgr = _make_postprocessor_manager()
        client = MagicMock()
        content_service = MagicMock()
        chat_service = MagicMock()

        _register_code_interpreter_postprocessors(
            tools=[_make_code_interpreter_tool()],
            postprocessor_manager=mgr,
            client=client,
            content_service=content_service,
            user_id="user-42",
            company_id="company-99",
            chat_id="chat-7",
            chat_service=chat_service,
        )

        pp: DisplayCodeInterpreterFilesPostProcessor = mgr.add_postprocessor.call_args_list[1][0][0]
        assert pp._client is client
        assert pp._company_id == "company-99"
        # All three IDs were passed, so short-term memory manager is initialised
        assert pp._short_term_memory_manager is not None


# ---------------------------------------------------------------------------
# First enabled CODE_INTERPRETER tool wins (break after first match)
# ---------------------------------------------------------------------------


class TestFirstMatchWins:
    @pytest.mark.ai
    def test_uses_config_from_first_enabled_code_interpreter_tool(self):
        """When multiple CODE_INTERPRETER tools are present, only the first enabled one is used."""
        from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
            ShowExecutedCodePostprocessorConfig,
        )

        first_config = CodeInterpreterExtendedConfig(
            executed_code_display_config=ShowExecutedCodePostprocessorConfig(
                sleep_time_before_display=0.1
            )
        )
        second_config = CodeInterpreterExtendedConfig(
            executed_code_display_config=ShowExecutedCodePostprocessorConfig(
                sleep_time_before_display=9.9
            )
        )
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[
                _make_code_interpreter_tool(config=first_config),
                _make_code_interpreter_tool(config=second_config),
            ],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        postprocessor: ShowExecutedCodePostprocessor = mgr.add_postprocessor.call_args_list[0][0][0]
        assert postprocessor._config.sleep_time_before_display == 0.1

    @pytest.mark.ai
    def test_skips_disabled_tool_and_uses_next_enabled_code_interpreter(self):
        """A disabled CODE_INTERPRETER tool is skipped; the next enabled one is used."""
        from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
            ShowExecutedCodePostprocessorConfig,
        )

        disabled_config = CodeInterpreterExtendedConfig(
            executed_code_display_config=ShowExecutedCodePostprocessorConfig(
                sleep_time_before_display=9.9
            )
        )
        enabled_config = CodeInterpreterExtendedConfig(
            executed_code_display_config=ShowExecutedCodePostprocessorConfig(
                sleep_time_before_display=0.5
            )
        )
        mgr = _make_postprocessor_manager()

        _register_code_interpreter_postprocessors(
            tools=[
                _make_code_interpreter_tool(is_enabled=False, config=disabled_config),
                _make_code_interpreter_tool(is_enabled=True, config=enabled_config),
            ],
            postprocessor_manager=mgr,
            client=MagicMock(),
            content_service=MagicMock(),
            user_id="u1",
            company_id="c1",
            chat_id="ch1",
            chat_service=MagicMock(),
        )

        postprocessor: ShowExecutedCodePostprocessor = mgr.add_postprocessor.call_args_list[0][0][0]
        assert postprocessor._config.sleep_time_before_display == 0.5
