"""
Streaming adapter for Claude Agent SDK → Unique platform.

Consumes the async event stream from claude-agent-sdk's query() and:
- forwards text deltas to the frontend via ChatService.modify_assistant_message_async()
- logs tool-call and turn events for diagnostics
- accumulates the full response text for post-processing

Key design decisions:
- Stream per text_delta chunk — no batching required.
- modify_assistant_message_async() is the only SDK call needed; transport to the
  frontend is the backend's responsibility and is not referenced here.
- accumulated_text carries the full text-to-date so each call is idempotent.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from logging import Logger
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKError,
    query,
)
from claude_agent_sdk.types import (
    ResultMessage,
    StreamEvent,
    ToolUseBlock,
)

from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.chat.service import ChatService

from .config import ClaudeAgentConfig


async def run_claude_loop(
    prompt: str,
    options: dict[str, Any],
    chat_service: ChatService,
    tool_progress_reporter: ToolProgressReporter,
    claude_config: ClaudeAgentConfig,
    logger: Logger,
) -> str:
    """Run the Claude Agent SDK query loop and return accumulated_text.

    Iterates over the async event stream from claude_agent_sdk.query():
    - content_block_delta / text_delta → accumulate text + stream via
      modify_assistant_message_async() to the frontend
    - assistant messages → log tool_use blocks; detect TodoWrite state
    - result → capture final text if no deltas were streamed
    - SDK errors → log, set user-facing error message, do NOT re-raise

    Returns accumulated_text string consumed by _run_post_processing().
    """
    verbose = claude_config.verbose_logging
    accumulated_text = ""
    tool_call_count = 0

    sdk_options_kwargs = dict(options)
    if claude_config.stderr_logging:

        def _stderr_handler(data: str) -> None:
            logger.debug("Claude Agent SDK stderr: %s", data.strip())

        sdk_options_kwargs["stderr"] = _stderr_handler

    sdk_options = ClaudeAgentOptions(**sdk_options_kwargs)

    try:
        # Pass prompt as an async iterable so the SDK uses stream_input(),
        # which keeps stdin open until the first result arrives before closing.
        # The string-prompt path closes stdin immediately via end_input(), which
        # breaks MCP control-request responses (CLIConnectionError: ProcessTransport
        # is not ready for writing). stream_input() is aware of sdk_mcp_servers and
        # waits for the first result before closing the channel.
        async def _prompt_iter() -> AsyncIterator[dict[str, Any]]:
            yield {
                "type": "user",
                "session_id": "",
                "message": {"role": "user", "content": prompt},
                "parent_tool_use_id": None,
            }

        turn = 0
        async for message in query(prompt=_prompt_iter(), options=sdk_options):
            if isinstance(message, StreamEvent):
                if message.event.get("type") == "message_start":
                    turn += 1
                accumulated_text = await _handle_stream_event(
                    message.event, accumulated_text, chat_service, logger, verbose, turn
                )
                continue

            if isinstance(message, AssistantMessage):
                tool_call_count = _handle_assistant_message(
                    message, tool_call_count, logger, verbose
                )
                continue

            if isinstance(message, ResultMessage):
                accumulated_text = _handle_result_message(
                    message, accumulated_text, tool_call_count, logger, verbose
                )
                continue

    except ClaudeSDKError as e:
        logger.error("Claude Agent SDK error: %s", e, exc_info=True)
        if not accumulated_text:
            accumulated_text = (
                "An error occurred while processing your request. Please try again."
            )

    except Exception as e:
        logger.error("Unexpected error in Claude Agent loop: %s", e, exc_info=True)
        if not accumulated_text:
            accumulated_text = (
                "An error occurred while processing your request. Please try again."
            )

    return accumulated_text


async def _handle_stream_event(
    event: dict[str, Any],
    accumulated_text: str,
    chat_service: ChatService,
    logger: Logger,
    verbose: bool,
    turn: int,
) -> str:
    """Process one StreamEvent. Returns updated accumulated_text."""
    event_type = event.get("type", "unknown")

    if event_type != "content_block_delta":
        _log_non_delta_event(event_type, event, turn, accumulated_text, verbose, logger)
        return accumulated_text

    delta = event.get("delta", {})
    if delta.get("type") != "text_delta":
        return accumulated_text

    text = delta.get("text", "")
    if not text:
        return accumulated_text

    accumulated_text += text
    await chat_service.modify_assistant_message_async(content=accumulated_text)
    return accumulated_text


def _log_non_delta_event(
    event_type: str,
    event: dict[str, Any],
    turn: int,
    accumulated_text: str,
    verbose: bool,
    logger: Logger,
) -> None:
    """Log diagnostic info for non-delta stream events."""
    if event_type == "message_start":
        if verbose:
            usage = event.get("message", {}).get("usage", {})
            logger.info(
                "[claude-agent] ← message_start | turn=%d | input_tokens=%s",
                turn,
                usage.get("input_tokens", "?"),
            )
    elif event_type == "message_stop":
        if verbose:
            logger.info(
                "[claude-agent] ← message_stop | turn=%d | streamed=%d chars",
                turn,
                len(accumulated_text),
            )
    elif verbose and event_type not in (
        "content_block_start",
        "content_block_stop",
        "ping",
    ):
        logger.debug("[claude-agent] ← event type=%s", event_type)


def _handle_assistant_message(
    message: AssistantMessage,
    tool_call_count: int,
    logger: Logger,
    verbose: bool,
) -> int:
    """Process one AssistantMessage. Returns updated tool_call_count."""
    for block in message.content:
        if not isinstance(block, ToolUseBlock):
            continue
        tool_call_count += 1
        input_preview = str(block.input)[:300]
        if verbose:
            logger.info(
                "[claude-agent] → tool_call #%d | tool=%s | input=%s",
                tool_call_count,
                block.name,
                input_preview,
            )
        else:
            logger.debug(
                "Claude agent tool call #%d: %s | input: %s",
                tool_call_count,
                block.name,
                input_preview,
            )
        if block.name == "TodoWrite":
            todos = (block.input or {}).get("todos", [])
            for todo in todos:
                status = todo.get("status", "?")
                content = todo.get("activeForm") or todo.get("content", "")
                logger.debug("todo [%s]: %s", status, content[:100])
    return tool_call_count


def _handle_result_message(
    message: ResultMessage,
    accumulated_text: str,
    tool_call_count: int,
    logger: Logger,
    verbose: bool,
) -> str:
    """Process ResultMessage. Returns accumulated_text (may be populated from result)."""
    if verbose:
        usage = getattr(message, "usage", None)
        logger.info(
            "[claude-agent] ← result | tool_calls=%d | final_text=%d chars%s",
            tool_call_count,
            len(accumulated_text),
            f" | usage={usage}" if usage else "",
        )
    if message.result and not accumulated_text:
        return message.result
    return accumulated_text
