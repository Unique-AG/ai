"""
Runner smoke test — exercises _run_claude_loop() end-to-end with real SDK.

Usage:
    cd unique_toolkit
    ANTHROPIC_API_KEY=<key> poetry run python ../.local-dev/smoke_test_runner.py
"""

import asyncio
import logging
import os
from unittest.mock import AsyncMock, MagicMock

from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.runner import ClaudeAgentRunner


def _make_runner_for_smoke() -> ClaudeAgentRunner:
    """Build a minimal ClaudeAgentRunner wired for smoke testing."""
    mock_event = MagicMock()
    mock_event.payload.user_message.text = "List three benefits of TDD"
    mock_event.payload.chat_id = "smoke-chat-001"
    mock_event.payload.assistant_message.id = "smoke-msg-001"
    mock_event.payload.user_metadata = None

    chat_service = MagicMock()

    chunks: list[str] = []

    async def _stream_chunk(content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            print(f"[stream chunk] {content!r}")
            chunks.append(content)

    chat_service.modify_assistant_message_async = AsyncMock(side_effect=_stream_chunk)
    chat_service._chunks = chunks

    config = ClaudeAgentConfig(
        system_prompt_override="You are a concise assistant. Answer in plain text.",
        model="claude-sonnet-4-5",
        max_turns=3,
        permission_mode="bypassPermissions",
    )

    return ClaudeAgentRunner(
        event=mock_event,
        logger=logging.getLogger("smoke_runner"),
        config=MagicMock(),
        claude_config=config,
        chat_service=chat_service,
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


async def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    logging.basicConfig(level=logging.DEBUG)

    runner = _make_runner_for_smoke()

    options = runner._build_options(
        system_prompt="You are a concise assistant. Answer in plain text.",
        workspace_dir=None,
    )

    print("=== Runner smoke test ===\n")
    print(f"Prompt: {runner._event.payload.user_message.text!r}\n")

    accumulated = await runner._run_claude_loop(
        prompt=runner._event.payload.user_message.text,
        options=options,
    )

    print("\n=== Accumulated text ===")
    print(accumulated)
    print(f"\n=== Done ({len(accumulated)} chars) ===")


if __name__ == "__main__":
    asyncio.run(main())
