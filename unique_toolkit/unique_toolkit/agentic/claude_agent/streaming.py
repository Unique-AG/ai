"""
Streaming adapter for Claude Agent SDK → Unique platform.

This module will contain helpers that consume the async event stream from
claude-agent-sdk's query() and forward text deltas to the frontend via
ChatService.modify_assistant_message_async().

Key design decisions:
- Stream per text_delta chunk — no batching required.
- modify_assistant_message_async() is the only SDK call needed; Python never
  touches AMQP directly.
- accumulated_text is maintained so each PATCH carries the full text to date.
"""

from __future__ import annotations
