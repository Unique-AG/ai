"""
Conversation history management for Claude Agent SDK integration.

This module will contain helpers for converting Unique platform history
(OpenAI-shaped MessageParam list from HistoryManager) into Anthropic-shaped
message history suitable for passing to claude-agent-sdk's query() call.

The runner maintains its own List[MessageParam] (Anthropic-shaped), appending
every observed event from the SDK stream. This is independent of UniqueAI's
HistoryManager, which uses OAI format. History ownership belongs to the runner;
Claude does not manage state internally across turns.

Key fields:
- max_history_interactions from ClaudeAgentConfig controls how many past
  turns are included in the system prompt when history_included=True.
"""
