"""
Conversation history text formatter for Claude Agent SDK integration.

Converts platform LanguageModelMessage history into a simple human-readable
text block that is injected into the system prompt. This matches Abi's Node
implementation where history is passed as a CHAT_HISTORY_SECTION string rather
than as structured Anthropic-format messages.

Step 3 (B9): Tool messages (LanguageModelToolMessage) are now rendered inline
after the assistant turn that triggered them, showing tool name, call arguments,
and a truncated result so subsequent turns retain full trace context.

Future: structured Anthropic-format history (list of {role, content} dicts)
will be returned by _build_history() once the SDK streaming loop is in place
and we move past MVP.
"""

from __future__ import annotations

import json
from typing import Any

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

_MAX_MESSAGE_CHARS = 2000
_TRUNCATION_SUFFIX = "... [truncated]"
_TOOL_RESULT_MAX_CHARS = 200

# (user_text, tool_lines, assistant_text)
_InteractionUnit = tuple[str, list[str], str]


def format_history_as_text(
    messages: list[LanguageModelMessage],
    max_interactions: int,
) -> str:
    """Format conversation history as a readable text block for the system prompt.

    Args:
        messages: List of LanguageModelMessage objects from HistoryManager.
        max_interactions: Maximum number of user+assistant interaction pairs to
            include. The most recent pairs are kept.

    Returns:
        Formatted text with "User: ..." / "[Tool: ...]" / "Assistant: ..." entries
        separated by blank lines. Tool messages are rendered inline between the
        user and assistant lines of the interaction that triggered them.
        Returns empty string when messages is empty or max_interactions is 0.
    """
    if not messages or max_interactions <= 0:
        return ""

    interactions = _group_interactions(messages)
    interactions = interactions[-max_interactions:]

    if not interactions:
        return ""

    formatted_parts: list[str] = []
    for user_text, tool_lines, assistant_text in interactions:
        user_line = f"User: {_truncate(_extract_text(user_text))}"
        assistant_line = f"Assistant: {_truncate(_extract_text(assistant_text))}"
        if tool_lines:
            tool_section = "\n".join(tool_lines)
            formatted_parts.append(f"{user_line}\n{tool_section}\n{assistant_line}")
        else:
            formatted_parts.append(f"{user_line}\n{assistant_line}")

    return "\n\n".join(formatted_parts)


def _group_interactions(
    messages: list[LanguageModelMessage],
) -> list[_InteractionUnit]:
    """Group messages into interaction units.

    Each unit: (user_text, [tool_lines], assistant_text).
    Tool lines are formatted as "[Tool: name(args)] truncated_result".
    Incomplete units (no assistant reply) are discarded — they represent the
    current in-flight turn.
    """
    interactions: list[_InteractionUnit] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if not isinstance(msg, LanguageModelUserMessage):
            i += 1
            continue

        user_text = _get_content(msg)
        # tool_call_id → (rendered_name, rendered_args) from intermediate assistant messages
        args_lookup: dict[str, tuple[str, str]] = {}
        tool_lines: list[str] = []
        assistant_text = ""

        j = i + 1
        while j < len(messages) and not isinstance(
            messages[j], LanguageModelUserMessage
        ):
            cur = messages[j]

            if isinstance(cur, LanguageModelAssistantMessage):
                if cur.tool_calls:
                    for fc in cur.tool_calls:
                        if fc.id:
                            name = fc.function.name if fc.function else ""
                            args = _render_args(
                                fc.function.arguments if fc.function else None
                            )
                            args_lookup[fc.id] = (name, args)
                else:
                    assistant_text = _get_content(cur)

            elif isinstance(cur, LanguageModelToolMessage):
                tc_id = cur.tool_call_id or ""
                if tc_id and tc_id in args_lookup:
                    call_name, call_args = args_lookup[tc_id]
                    if call_args:
                        label = f"[Tool: {call_name}({call_args})]"
                    else:
                        label = f"[Tool: {call_name}]" if call_name else "[Tool]"
                else:
                    msg_name = cur.name or ""
                    label = f"[Tool: {msg_name}]" if msg_name else "[Tool]"

                content = _get_content(cur)
                tool_lines.append(f"{label} {_truncate_tool_result(content)}")

            j += 1

        if assistant_text:
            interactions.append((user_text, tool_lines, assistant_text))

        i = j

    return interactions


def _render_args(arguments: dict[str, Any] | None) -> str:
    """Render tool call arguments as key="value" pairs, truncated to ~100 chars."""
    if not arguments:
        return ""
    parts = [f'{k}="{v}"' for k, v in arguments.items()]
    result = ", ".join(parts)
    if len(result) > 100:
        result = result[:97] + "..."
    return result


def _truncate_tool_result(text: str) -> str:
    """Truncate tool result content to _TOOL_RESULT_MAX_CHARS."""
    if len(text) <= _TOOL_RESULT_MAX_CHARS:
        return text
    return text[:_TOOL_RESULT_MAX_CHARS] + "..."


def _get_content(message: LanguageModelMessage) -> str:
    """Extract raw content from a message as a string."""
    if message.content is None:
        return ""
    if isinstance(message.content, str):
        return message.content
    # list[dict] — e.g. multimodal content; stringify for history purposes
    return json.dumps(message.content)


def _extract_text(content: str) -> str:
    """Return content string, defaulting empty content to a placeholder."""
    return content if content else ""


def _truncate(text: str) -> str:
    """Truncate text to _MAX_MESSAGE_CHARS, appending a suffix when cut."""
    if len(text) <= _MAX_MESSAGE_CHARS:
        return text
    return text[:_MAX_MESSAGE_CHARS] + _TRUNCATION_SUFFIX
