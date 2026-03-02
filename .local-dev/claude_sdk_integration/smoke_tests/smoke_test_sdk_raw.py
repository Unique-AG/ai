"""
Raw SDK inspection script — verify real event shapes from claude_agent_sdk.

Usage:
    cd unique_toolkit
    ANTHROPIC_API_KEY=<key> poetry run python ../.local-dev/smoke_test_sdk_raw.py
"""

import asyncio
import os

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    UserMessage,
)


async def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant. Be concise.",
        model="claude-sonnet-4-6",
        max_turns=1,
        permission_mode="bypassPermissions",
        env={"ANTHROPIC_API_KEY": api_key},
        include_partial_messages=True,
    )

    print("=== Raw SDK event inspection ===\n")
    event_count = 0

    async for message in query(prompt="Reply with exactly: hello", options=options):
        event_count += 1
        type_name = type(message).__name__
        print(f"[{event_count}] type={type_name}")

        if isinstance(message, StreamEvent):
            print(f"    .uuid={message.uuid!r}")
            print(f"    .session_id={message.session_id!r}")
            print(f"    .parent_tool_use_id={message.parent_tool_use_id!r}")
            print(f"    .event={message.event}")
            event_type = message.event.get("type", "?")
            print(f"    event['type']={event_type!r}")
            if event_type == "content_block_delta":
                delta = message.event.get("delta", {})
                print(f"    delta={delta}")
                print(f"    delta['type']={delta.get('type')!r}")
                print(f"    delta['text']={delta.get('text')!r}")

        elif isinstance(message, AssistantMessage):
            print(f"    .model={message.model!r}")
            print(f"    .content={message.content!r}")
            for block in message.content:
                print(f"    block type={type(block).__name__}")

        elif isinstance(message, ResultMessage):
            print(f"    .subtype={message.subtype!r}")
            print(f"    .result={message.result!r}")
            print(f"    .is_error={message.is_error!r}")
            print(f"    .total_cost_usd={message.total_cost_usd!r}")

        elif isinstance(message, SystemMessage):
            print(f"    .subtype={message.subtype!r}")
            print(f"    .data={message.data!r}")

        elif isinstance(message, UserMessage):
            print(f"    .content={message.content!r}")

        print()

    print(f"=== Done: {event_count} events total ===")


if __name__ == "__main__":
    asyncio.run(main())
