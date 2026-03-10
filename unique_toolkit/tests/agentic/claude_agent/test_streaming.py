"""
Unit tests for unique_toolkit.agentic.claude_agent.streaming

All claude_agent_sdk.query() calls are mocked — these tests are CI-safe and
do not spawn a subprocess or require a real Anthropic API key.

Naming convention: test_<function>_<scenario>_<expected>
"""

from __future__ import annotations

from logging import Logger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeSDKError
from claude_agent_sdk.types import (
    ResultMessage,
    StreamEvent,
    ToolUseBlock,
)

from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.streaming import run_claude_loop

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _mock_query_gen(*messages):
    """Async generator that yields each provided mock message."""
    for msg in messages:
        yield msg


async def _raising_gen(exc: Exception):
    """Async generator that raises exc on first iteration."""
    raise exc
    yield  # pragma: no cover — makes this a generator


def _make_chat_service() -> MagicMock:
    svc = MagicMock()
    svc.modify_assistant_message_async = AsyncMock()
    return svc


def _make_logger() -> MagicMock:
    return MagicMock(spec=Logger)


def _call_run_claude_loop(
    mock_query_return, *, config: ClaudeAgentConfig | None = None
):
    """Helper: call run_claude_loop with mocked query and return (result, chat_service)."""
    chat_service = _make_chat_service()
    config = config or ClaudeAgentConfig()

    async def _run():
        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = mock_query_return
            return await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=config,
                logger=_make_logger(),
            )

    return _run, chat_service


# ─────────────────────────────────────────────────────────────────────────────
# run_claude_loop
# ─────────────────────────────────────────────────────────────────────────────


class TestRunClaudeLoop:
    @pytest.mark.asyncio
    async def test_streams_text_deltas_to_chat_service(self) -> None:
        """Each text_delta calls modify_assistant_message_async with growing text."""
        chat_service = _make_chat_service()

        delta1 = StreamEvent(
            uuid="uuid-1",
            session_id="session-1",
            event={
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "Hello"},
            },
            parent_tool_use_id=None,
        )
        delta2 = StreamEvent(
            uuid="uuid-2",
            session_id="session-1",
            event={
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": " world"},
            },
            parent_tool_use_id=None,
        )

        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = _mock_query_gen(delta1, delta2)
            await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=ClaudeAgentConfig(),
                logger=_make_logger(),
            )

        calls = chat_service.modify_assistant_message_async.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["content"] == "Hello"
        assert calls[1].kwargs["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_returns_accumulated_text(self) -> None:
        """Return value is the full concatenated text from all text_deltas."""
        chat_service = _make_chat_service()

        delta1 = StreamEvent(
            uuid="uuid-1",
            session_id="session-1",
            event={
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "Hello"},
            },
            parent_tool_use_id=None,
        )
        delta2 = StreamEvent(
            uuid="uuid-2",
            session_id="session-1",
            event={
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": " world"},
            },
            parent_tool_use_id=None,
        )

        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = _mock_query_gen(delta1, delta2)
            result = await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=ClaudeAgentConfig(),
                logger=_make_logger(),
            )

        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_handles_result_message_when_no_text_accumulated(self) -> None:
        """When no text_deltas were received, result.result is used as accumulated text."""
        chat_service = _make_chat_service()

        result_msg = ResultMessage(
            subtype="success",
            duration_ms=100,
            duration_api_ms=100,
            is_error=False,
            num_turns=1,
            session_id="session-1",
            result="Final answer text",
        )

        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = _mock_query_gen(result_msg)
            result = await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=ClaudeAgentConfig(),
                logger=_make_logger(),
            )

        assert result == "Final answer text"

    @pytest.mark.asyncio
    async def test_logs_tool_use_blocks(self) -> None:
        """tool_use blocks in AssistantMessage content trigger debug log with tool name."""
        chat_service = _make_chat_service()
        logger = _make_logger()

        tool_block = ToolUseBlock(
            id="tu-1",
            name="mcp__unique_platform__search_knowledge_base",
            input={"search_query": "interest rates"},
        )
        assistant_msg = AssistantMessage(
            content=[tool_block],
            model="claude-sonnet-4-5",
        )

        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = _mock_query_gen(assistant_msg)
            await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=ClaudeAgentConfig(),
                logger=logger,
            )

        debug_calls = [str(c) for c in logger.debug.call_args_list]
        assert any(
            "mcp__unique_platform__search_knowledge_base" in c for c in debug_calls
        )

    @pytest.mark.asyncio
    async def test_catches_sdk_error_gracefully(self) -> None:
        """ClaudeSDKError does not propagate; returns a user-facing error string."""
        chat_service = _make_chat_service()
        logger = _make_logger()

        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = _raising_gen(ClaudeSDKError("sdk exploded"))
            result = await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=ClaudeAgentConfig(),
                logger=logger,
            )

        assert "error" in result.lower()
        logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_catches_generic_exception_gracefully(self) -> None:
        """Unexpected exceptions do not propagate; returns a user-facing error string."""
        chat_service = _make_chat_service()
        logger = _make_logger()

        with patch("unique_toolkit.agentic.claude_agent.streaming.query") as mock_query:
            mock_query.return_value = _raising_gen(RuntimeError("boom"))
            result = await run_claude_loop(
                prompt="hi",
                options={},
                chat_service=chat_service,
                tool_progress_reporter=MagicMock(),
                claude_config=ClaudeAgentConfig(),
                logger=logger,
            )

        assert "error" in result.lower()
        logger.error.assert_called()
